"""Minimal SDH (SSE/SSQ) block reader (layout: notes/integration/audio.md section 2)."""
import struct
def blocks(b):
    if b[:4] != b"SDRH": return {}
    w = struct.unpack_from("<I", b, 8)[0]; p = (w & 0xff) * 16; out = {}
    while p + 8 <= len(b):
        tag = b[p:p + 2]; hdr, size = struct.unpack_from("<HH", b, p + 2)
        if tag == b"WD": size = struct.unpack_from("<I", b, p + 4)[0] // 16 if False else size
        if not tag.isalpha() or size == 0: break
        out[tag.decode()] = (p, hdr)
        if tag == b"WD": break
        p += size * 16
    return out
def fe(b):
    bl = blocks(b)
    if "FE" not in bl: return None
    p, hdr = bl["FE"]; n = struct.unpack_from("<H", b, p + 6)[0]; sid = struct.unpack_from("<H", b, p + 8)[0]
    ents = [struct.unpack_from("<HH", b, p + hdr * 16 + 4 * i) for i in range(n)]
    return sid, ents
def wv(b):
    bl = blocks(b)
    if "WV" not in bl: return None
    p, hdr = bl["WV"]; return struct.unpack_from("<HH", b, p + 8)        # (count, wave-bank id)
