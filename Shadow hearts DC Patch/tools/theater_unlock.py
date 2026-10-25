"""Unlock every Theater scene in the running US game (title screen): common[1] = 1 and the 162 scene bits from common[2],
in both the live system common block (EE 0x100000) and TitleShared (0x45e940).  A later save writes them to the memory card."""
import sys, struct
sys.path.insert(0, r"C:\Users\jamie\Documents\SH2\Sh2 Decomp\sh2-decomp\tools\live")
import dbg
d = dbg.DebugServer()
bits = bytearray(21)
for k in range(162): bits[k >> 3] |= 1 << (k & 7)
for base in (0x100000, 0x45e940):
    cur = bytearray(d.mem(base, 0x20))
    cur[1] = 1
    for j, b in enumerate(bits): cur[2 + j] |= b
    r = d.send(cmd="write_memory", cpu="ee", address="0x%x" % base, data=bytes(cur).hex()); assert r.get("ok"), r
    print(hex(base), d.mem(base, 0x18).hex())
