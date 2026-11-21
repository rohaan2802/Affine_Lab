"""Export exact JSON ciphertext fields from the real loopback PCAP using TShark."""
import csv
import json
import os
import subprocess
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TSHARK = os.environ.get('TSHARK') or shutil.which('tshark') or '/home/codetech/.local/psy-tools/bin/tshark'


def main():
    pcap = ROOT / 'evidence/capture.pcap'
    fields = ['frame.number', 'frame.time_epoch', 'tcp.stream', 'tcp.srcport',
              'tcp.dstport', 'tcp.seq', 'tcp.payload']
    cmd = [TSHARK, '-r', str(pcap), '-Y', 'tcp.port == 9999 && tcp.len > 0', '-T', 'fields']
    for field in fields:
        cmd += ['-e', field]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    (ROOT / 'evidence/packet_payloads.tsv').write_text(result.stdout)
    streams = defaultdict(lambda: {'request': {}, 'response': {}, 'frames': []})
    for line in result.stdout.splitlines():
        frame, stamp, index, src, dst, seq, payload = line.split('\t')
        stream = streams[int(index)]
        direction = 'request' if dst == '9999' else 'response'
        for offset, byte in enumerate(bytes.fromhex(payload.replace(':', ''))):
            position = int(seq) + offset
            if position in stream[direction]:
                assert stream[direction][position] == byte, 'Conflicting TCP retransmission'
            stream[direction][position] = byte
        stream['frames'].append(int(frame))
        stream.setdefault('time', stamp)
    rows = []
    sessions = []
    for index, stream in sorted(streams.items()):
        objects = {}
        for direction in ['request', 'response']:
            positions = sorted(stream[direction])
            if not positions:
                continue
            assert positions == list(range(positions[0], positions[-1]+1)), 'TCP gap'
            objects[direction] = json.loads(bytes(stream[direction][p] for p in positions))
        if not {'request', 'response'} <= objects.keys():
            continue
        assert 'ciphertext' in objects['response'], 'Server error or incomplete run'
        session = len(sessions) + 1
        mood = objects['request']['mood']
        for direction, field in [('Client->Server', 'username_enc'),
                                 ('Client->Server', 'message_enc'), ('Server->Client', 'ciphertext')]:
            obj = objects['request' if direction.startswith('Client') else 'response']
            cipher = obj[field]
            rows.append({'session': session, 'direction': direction, 'field': field,
                         'mood': mood, 'tcp_stream': index, 'timestamp_epoch': stream['time'],
                         'length_chars': len(cipher), 'ciphertext': cipher})
        sessions.append({'session': session, 'tcp_stream': index, 'mood': mood,
                         'frames': stream['frames'], **objects})
        follow = subprocess.run([TSHARK, '-r', str(pcap), '-q', '-z', f'follow,tcp,ascii,{index}'],
                                capture_output=True, text=True, check=True)
        (ROOT / f'evidence/session_{session}_follow_tcp.txt').write_text(follow.stdout)
    assert len(sessions) == 5 and len(rows) == 15, 'Expected five complete sessions'
    with (ROOT / 'ciphertexts.csv').open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (ROOT / 'output/captured_sessions.json').write_text(json.dumps(sessions, indent=2))
    print(f'Captured {len(sessions)} complete sessions, {len(rows)} exact ciphertext fields.')


if __name__ == '__main__':
    main()
