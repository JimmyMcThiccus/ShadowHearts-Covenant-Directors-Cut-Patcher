"""Live prep for the Mr. Meiyuan card test (run on the debug map, then `dcscene.py meiyuan go`).
Fakes the Shadow Hearts 1 save bonus: ParamChange(0, 0x400, -1) = InventoryChange(0x400) -> GS chunk +0x70 & 0x3f, latched at
New Game from common byte 0x100082 (set by the title screen's BASLUS-20347 memory-card scan).  GS = first FLDa chunk at 0x1022fc
(GetGameSection: save object at gp-0x7b94, gp 0x4479f0).  Also drops costume 10 (so Pierre can give it), sets 50000 Cash."""
import sys, struct
sys.path.insert(0, r"C:\Users\jamie\Documents\SH2\Sh2 Decomp\sh2-decomp\tools\live")
import dbg
d = dbg.DebugServer()
def wr(a, b):
    r = d.send(cmd="write_memory", cpu="ee", address="0x%x" % a, data=bytes(b).hex()); assert r.get("ok"), r
BTL0, MENU, GS = 0x100130, 0x102d2c, 0x1022fc
assert d.mem(GS, 2) == b"GS"
bag = d.mem(BTL0 + 2, 1)[0]
wr(GS + 0x70, [(d.mem(GS + 0x70, 1)[0] & 0xc0) | 1])
wr(MENU + 4 + 4 * bag, struct.pack("<I", 50000))                       # SetCurrentCash: MENU+4 + 4*active bag
wr(0x10106c, struct.pack("<H", struct.unpack("<H", d.mem(0x10106c, 2))[0] & ~(1 << 10)))
wr(MENU + 0x2fc, struct.pack("<I", d.u32(MENU + 0x2fc) & ~(1 << 10)))
if struct.unpack("<H", d.mem(0x10106e, 2))[0] == 10: wr(0x10106e, struct.pack("<H", 0))
kb = BTL0 + 0xabc + bag * 0x200 + 0x30
card = d.mem(kb + 148 // 8, 1)[0]                                         # 'card' = already won it (key 148), else drop it
wr(kb + 148 // 8, [(card | (1 << (148 % 8))) if "card" in sys.argv else (card & ~(1 << (148 % 8)) & 0xff)])
print("map %s  SH1 %#x  cash %d  costumes %#x  collection %#x  card %d" % (d.mem(GS + 0x10, 16).split(b"\0")[0].decode(),
      d.mem(GS + 0x70, 1)[0], d.u32(MENU + 4 + 4 * bag), struct.unpack("<H", d.mem(0x10106c, 2))[0], d.u32(MENU + 0x2fc),
      (d.mem(kb + 148 // 8, 1)[0] >> (148 % 8)) & 1))
