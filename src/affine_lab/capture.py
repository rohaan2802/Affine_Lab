"""Read bounded IPv4/TCP PCAPs and reassemble the lab's JSON messages.

No capture permissions, Wireshark installation or third-party parser is
needed to inspect the included evidence. Supports Ethernet, Linux cooked
v1 and raw IPv4 links. Rejects gaps/conflicting retransmissions rather than
silently manufacturing a complete stream. Not a general network analyzer.
"""

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import struct

MAX_PCAP_BYTES = 64 * 1024 * 1024
MAX_STREAM_BYTES = 1024 * 1024


class CaptureError(ValueError):
    pass


def reassemble(segments: list[tuple[int, bytes]]) -> bytes:
    data: dict[int, int] = {}
    for sequence, payload in segments:
        if len(data) + len(payload) > 2 * MAX_STREAM_BYTES:
            raise CaptureError("stream exceeds the lab payload limit")
        for offset, byte in enumerate(payload):
            position = sequence + offset
            if position in data and data[position] != byte:
                raise CaptureError("conflicting TCP retransmission")
            data[position] = byte
    if not data:
        return b""
    low, high = min(data), max(data)
    if high - low + 1 != len(data):
        raise CaptureError("TCP sequence gap; capture is incomplete")
    if len(data) > MAX_STREAM_BYTES:
        raise CaptureError("stream exceeds the lab payload limit")
    return bytes(data[p] for p in range(low, high + 1))


def inspect_pcap(path: Path, port: int = 9999) -> dict:
    if type(port) is not int or not 1 <= port <= 65535:
        raise CaptureError("port must be from 1 to 65535")
    size = path.stat().st_size
    if not 24 <= size <= MAX_PCAP_BYTES:
        raise CaptureError("PCAP must be between 24 bytes and 64 MiB")
    raw = path.read_bytes()
    formats = {
        b"\xd4\xc3\xb2\xa1": ("<", 1_000_000),
        b"\xa1\xb2\xc3\xd4": (">", 1_000_000),
        b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000),
        b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000),
    }
    if raw[:4] not in formats:
        raise CaptureError("unsupported capture format; classic PCAP is required")
    endian, precision = formats[raw[:4]]
    major, minor, _, _, snaplen, linktype = struct.unpack(endian + "HHiiii", raw[4:24])
    if (major, minor) != (2, 4) or linktype not in {1, 101, 113}:
        raise CaptureError("unsupported PCAP version or link type")
    streams = defaultdict(
        lambda: {"client": [], "server": [], "frames": [], "start": None}
    )
    frames, skipped, offset = 0, 0, 24
    while offset < len(raw):
        if len(raw) - offset < 16:
            raise CaptureError("truncated packet header")
        seconds, fraction, length, original_length = struct.unpack(
            endian + "IIII", raw[offset : offset + 16]
        )
        offset += 16
        if length > snaplen or length > len(raw) - offset or length > original_length:
            raise CaptureError("truncated or invalid packet length")
        packet = raw[offset : offset + length]
        offset += length
        frames += 1
        if frames > 100_000:
            raise CaptureError("too many packets for this lab inspector")
        ip_offset = 14 if linktype == 1 else 16 if linktype == 113 else 0
        if linktype == 1:
            if len(packet) < 14:
                raise CaptureError("short Ethernet frame")
            ethertype = struct.unpack("!H", packet[12:14])[0]
            if ethertype == 0x8100 and len(packet) >= 18:
                ethertype = struct.unpack("!H", packet[16:18])[0]
                ip_offset = 18
            if ethertype != 0x0800:
                skipped += 1
                continue
        if linktype == 113 and (len(packet) < 16 or packet[14:16] != b"\x08\x00"):
            skipped += 1
            continue
        ip = packet[ip_offset:]
        if len(ip) < 20 or ip[0] >> 4 != 4:
            skipped += 1
            continue
        ihl = (ip[0] & 15) * 4
        total = struct.unpack("!H", ip[2:4])[0]
        if ihl < 20 or total < ihl or total > len(ip):
            raise CaptureError("truncated IPv4 packet")
        if ip[9] != 6:
            skipped += 1
            continue
        if struct.unpack("!H", ip[6:8])[0] & 0x3FFF:
            raise CaptureError("fragmented IPv4 is outside this lab inspector's scope")
        tcp = ip[ihl:total]
        if len(tcp) < 20:
            raise CaptureError("truncated TCP header")
        src_port, dst_port, sequence = struct.unpack("!HHI", tcp[:8])
        if port not in (src_port, dst_port):
            skipped += 1
            continue
        src = str(ipaddress.IPv4Address(ip[12:16]))
        dst = str(ipaddress.IPv4Address(ip[16:20]))
        if src != "127.0.0.1" or dst != "127.0.0.1":
            raise CaptureError("lab traffic must be confined to 127.0.0.1")
        header = (tcp[12] >> 4) * 4
        if not 20 <= header <= len(tcp):
            raise CaptureError("invalid TCP data offset")
        client_port = src_port if dst_port == port else dst_port
        stream = streams[client_port]
        stream["frames"].append(frames)
        if stream["start"] is None:
            stream["start"] = seconds + fraction / precision
        payload = tcp[header:]
        if payload:
            stream["client" if dst_port == port else "server"].append(
                (sequence, payload)
            )
    sessions = []
    for client_port, stream in sorted(
        streams.items(), key=lambda item: item[1]["start"]
    ):
        request, response = reassemble(stream["client"]), reassemble(stream["server"])
        if not request and not response:
            continue
        if not request or not response:
            raise CaptureError("incomplete request/reply stream")
        try:
            req, resp = json.loads(request), json.loads(response)
        except (ValueError, UnicodeError) as exc:
            raise CaptureError(
                "captured stream is not one complete UTF-8 JSON request/reply"
            ) from exc
        if (
            not isinstance(req, dict)
            or not isinstance(resp, dict)
            or "ciphertext" not in resp
        ):
            raise CaptureError("stream does not contain the lab reply schema")
        sessions.append(
            {
                "session": len(sessions) + 1,
                "client_port": client_port,
                "start_utc": datetime.fromtimestamp(
                    stream["start"], timezone.utc
                ).isoformat(),
                "frames": stream["frames"],
                "request": req,
                "response": resp,
            }
        )
    if not sessions:
        raise CaptureError("no complete lab sessions were found")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": size,
        "frames": frames,
        "skipped_frames": skipped,
        "linktype": linktype,
        "port": port,
        "sessions": sessions,
    }
