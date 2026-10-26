"""Graft a subtitle pack (SBTD payload) into an LSD with new line times, padded to the target's packet size so nothing else moves.
usage: lsd_swap_sbtd.py IN.LSD NEW.sbtd TIMES.json OUT.LSD      (TIMES.json = [[start, end], ...] in seconds, one per line)"""
import sys, struct, json, lsdtracks
b = bytearray(open(sys.argv[1], "rb").read()); s = bytearray(open(sys.argv[2], "rb").read()); times = json.load(open(sys.argv[3]))
nl = struct.unpack_from("<h", s, 0)[0]; lt = struct.unpack_from("<I", s, 0x14)[0]; assert nl == len(times)
for i, (a, e) in enumerate(times): struct.pack_into("<ff", s, lt + i*0x20 + 0x14, a, e)
n, tps, dur, tr = lsdtracks.tracks(b)
k = [i for i in range(n) if tr[i][1] == "SBTD"][0]; hdr = 0x40 + sum(t[5] for t in tr[:k])
room = struct.unpack_from("<I", b, hdr + 0x18)[0] * 16
p = 0x40 + sum(t[5] for t in tr); hits = 0
while p < len(b):
    t, _, seq, nb = struct.unpack_from("<HHII", b, p)
    if t == k:
        assert nb * 16 == room and len(s) <= room, (nb, room, len(s)); b[p+16:p+16+room] = bytes(s) + bytes(room - len(s)); hits += 1
    p += 16 + nb*16
assert hits == 1
open(sys.argv[4], "wb").write(b); print("SBTD track %d: %d lines, %d bytes in a %d-byte packet ->" % (k, nl, len(s), room), sys.argv[4])
