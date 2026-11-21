"""Read the instructor's embedded Python 3.12 server without launching its binary."""
import marshal
import struct
import zlib
from pathlib import Path


def load_server_code():
    data = (Path(__file__).parent / 'original_server').read_bytes()
    cookie = data.rfind(b'MEI\x0c\x0b\x0a\x0b\x0e')
    if cookie < 0:
        raise ValueError('PyInstaller archive missing')
    _, total, offset, size, version, _ = struct.unpack('!8sIIII64s', data[cookie:cookie+88])
    if version != 312:
        raise RuntimeError('Use WSL Python 3.12')
    start = cookie + 88 - total
    toc = data[start+offset:start+offset+size]
    pos = 0
    while pos < len(toc):
        length, off, packed, unpacked, compressed, kind = struct.unpack('!IIIIBc', toc[pos:pos+18])
        name = toc[pos+18:pos+length].split(b'\0')[0]
        pos += length
        if name == b'server' and kind == b's':
            raw = data[start+off:start+off+packed]
            if compressed:
                raw = zlib.decompress(raw)
            assert len(raw) == unpacked
            return marshal.loads(raw)
    raise ValueError('Server module missing')
