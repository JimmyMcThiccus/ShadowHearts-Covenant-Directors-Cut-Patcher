"""Set up a DC shared-map scene on the debug map and warp there.  usage: dcscene.py PRESET [go]
Flags are bits of the register file, reg8[i] is its byte i; 'go' drives Circle+R3 > Down x3 > Cross (debug map only)."""
import sys, struct, time
sys.path.insert(0, r"C:\Users\jamie\Documents\SH2\Sh2 Decomp\sh2-decomp\tools\live")
import dbg, flagnames
PRESETS = {   # map, {flag: 0/1}, {reg8 index: value}
    "lucia":     ("MS_00_U", {}, {0x334: 1}),
    "anastasia": ("FI_00_U", {75: 1, 10719: 0, 7065: 0}, {0x328: 50}),
    "curry":     ("RE_03_U", {105: 1, 9634: 0, 3361: 1}, {}),   # 3361 clear bounces to RE_00_U (disc 2 scene N077)
    "joachim":   ("IN_00_U", {7437: 1, 7443: 1, 7442: 0, 8413: 0, 7441: 1}, {0x3a0: 3}),   # 7441 clear jumps to GY_00_D (disc 2 scene N123)
    "joachim_us": ("IN_00_U", {7437: 1, 7443: 1, 7442: 0, 8413: 1, 7441: 1}, {0x3a0: 3}),   # control: DC lines already seen, pure US path
    "neam":      ("ND_03_U", {620: 1}, {104: 0}),   # flag 620 routes ND_03_U/ND_05_U exits to ND_04_A (the warp cannot encode _A)
    # Jimote's treasure-chest game: 14 = Jimote present, 3404 met, 3410/3411 tiers 2-3 seen, 84 story gate for tier 4 (1000 Cash, Mr. Meiyuan card), 3412 = tier 4 intro
    "meiyuan":   ("WI_13_U", {14: 1, 3404: 1, 39: 1, 3410: 1, 60: 1, 3411: 1, 84: 1, 3412: 0}, {}),
    # Pierre (char 7, always there): talking to him (event 10) runs the Beautiful Fool scene if !298, card 2708, costumes 1793-1801, !1802
    "pierre":    ("PA_03_U", {298: 0}, {}),
    # Nelson's boat = CA_02_U event 4, reached through a look point at the rowboat (-82.3, 21.7, -272.1), radius 15, that the start
    # function only registers when flag 4610 is set (box id 4 never accepts Cross: its flags 0x11 lack bit 2).  73 = Nelson's crew
    # present, 42 clear = Nahash not done; world-map point 18 (WM chunk 0x102c8c +0x10+18) must not be state 2, or the branch skips Nahash
    "boat":      ("CA_02_U", {4610: 1, 73: 1, 42: 0}, {}),
    # Gourmet Connoisseur Ginori (FI_01_U char 16, event 31): his rounds load FI_EV00B / 01B / 02B, swapped by the UnDub voice banks
    "ginori":    ("FI_01_U", {}, {}),
}
d = dbg.DebugServer()
def wr(a, b):
    r = d.send(cmd="write_memory", cpu="ee", address="0x%x" % a, data=bytes(b).hex()); assert r.get("ok"), r
name = sys.argv[1]; mp, flags, regs = PRESETS[name]
rf = flagnames.register_file(d); assert rf, "no field script running (be on the debug map)"
for n, v in flags.items():
    b = d.mem(rf + n // 8, 1)[0]; b = (b | (1 << (n % 8))) if v else (b & ~(1 << (n % 8)) & 0xff); wr(rf + n // 8, [b])
for i, v in regs.items(): wr(rf + i, [v])
wr(rf + flagnames.WARP_REG * 4, struct.pack("<I", flagnames.encode_map(mp)))
print("regfile %#x: %s set, warp -> %s" % (rf, name, mp),
      {n: (d.mem(rf + n // 8, 1)[0] >> (n % 8)) & 1 for n in flags}, {hex(i): d.mem(rf + i, 1)[0] for i in regs})
if "go" in sys.argv:
    import keys
    keys.down("4"); time.sleep(0.15); keys.tap("L", 0.15); time.sleep(0.1); keys.up("4"); time.sleep(0.8)
    for _ in range(3): keys.tap("Down", 0.15); time.sleep(0.25)
    keys.tap("K", 0.15); print("warp keys sent")
