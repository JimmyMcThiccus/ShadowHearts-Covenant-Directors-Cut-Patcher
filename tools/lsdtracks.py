"""List LSD track headers.  usage: lsdtracks.py TAG PATH"""
import sys, struct, isoset
def tracks(b):
    assert b[:4] == b"LSDH"
    n, tps = struct.unpack_from("<H", b, 0xa)[0], struct.unpack_from("<H", b, 0xe)[0]
    dur = struct.unpack_from("<I", b, 0x10)[0]
    p = 0x40; out = []
    for i in range(n):
        tag = b[p:p+4]; fl, t0, t1 = struct.unpack_from("<III", b, p+4); hs, mode = struct.unpack_from("<HH", b, p+0x10)
        tot = struct.unpack_from("<I", b, p+0x18)[0]
        name = b[p+0x20:p+0x30].split(b"\0")[0]
        extra = ""
        if tag == b"MOVS": extra = "%dx%d" % struct.unpack_from("<HH", b, p+0x28)
        out.append((i, tag.decode("latin1"), fl, t0, t1, hs*16, mode, tot*16, name, extra)); p += hs*16
    return n, tps, dur, out
if __name__ == "__main__":
    d = isoset.Disc(sys.argv[1]); b = d.read(sys.argv[2])
    n, tps, dur, tr = tracks(b)
    print(sys.argv[1], sys.argv[2], len(b), "tracks", n, "tps", tps, "dur", dur, "(%.1fs)" % (dur/tps))
    for t in tr: print("  ", t)
