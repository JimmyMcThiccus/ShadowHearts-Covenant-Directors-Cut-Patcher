"""Minimal MSD / MDT reader (layout: sh2_menu::msd).  chunks(data) -> [(off, type, ptrcount, base, stride, count, next)]"""
import struct
def chunks(d):
    out = []; o = 0
    while True:
        ty, pc, _, base, stride, count, nxt = struct.unpack_from("<HBBHHII", d, o)
        out.append((o, ty, pc, base, stride, count, nxt))
        if nxt == 0: return out
        o += nxt
def attaches(d):
    for o, ty, pc, base, stride, count, nxt in chunks(d):
        if stride == 12 and count > 5:
            recs = [struct.unpack_from("<III", d, o + 16 + 12 * i) for i in range(count)]
            if all(r[0] + r[2] <= len(d) for r in recs): return o, recs
    return None, []
def cstr(d, p): return d[p:d.index(b"\0", p)]
