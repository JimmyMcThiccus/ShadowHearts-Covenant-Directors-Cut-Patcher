"""Replace the PCMS payload of an LSD in place (same packet layout, same size).  usage: lsd_swap_pcms.py IN.LSD NEW.pcms OUT.LSD"""
import sys, struct, lsdtracks
b = bytearray(open(sys.argv[1], "rb").read()); new = open(sys.argv[2], "rb").read()
n, tps, dur, tr = lsdtracks.tracks(b)
pc = [k for k in range(n) if tr[k][1] == "PCMS"][0]
p = 0x40 + sum(t[5] for t in tr); q = 0
while p < len(b):
    t, _, seq, nb = struct.unpack_from("<HHII", b, p)
    if t == pc: b[p+16:p+16+nb*16] = new[q:q+nb*16]; q += nb*16
    p += 16 + nb*16
assert q == len(new), (q, len(new))
open(sys.argv[3], "wb").write(b); print("swapped", q, "bytes of PCMS (track %d) ->" % pc, sys.argv[3])
