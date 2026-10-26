"""Live helper for the DC-injection test.  status | patch <PKFINFO_patched.TBL> | replace <OLD.iso> <NEW.iso> | warp <MAP_NAME>
replace: after a PCSX2 Change Disc to NEW.iso (e.g. the disc 2 build), load its whole table; root entries 0..13 hold absolute LBAs
in RAM, so each is mapped OLD LBA -> root file name -> NEW LBA.
FileIOLib (US) at 0x7247f4: header copy +0x60, PkbEntry[5000] +0x70, u64 entry count +0x13abc (found live 2026-10-24)."""
import sys, struct
sys.path.insert(0, r"C:\Users\jamie\Documents\SH2\Sh2 Decomp\sh2-decomp\tools\live")
import dbg, flagnames
FIO = 0x7247f4; HDR = FIO + 0x60; ENT = FIO + 0x70; CNT = FIO + 0x13abc
d = dbg.DebugServer()
def write(a, data):
    for i in range(0, len(data), 1024):
        r = d.send(cmd="write_memory", cpu="ee", address="0x%x" % (a + i), data=data[i:i+1024].hex())
        if not r.get("ok"): raise RuntimeError(r)
def status():
    n, es, tot = struct.unpack("<HHI", d.mem(HDR, 8)); c = struct.unpack("<Q", d.mem(CNT, 8))[0]
    rf = flagnames.register_file(d)
    w = struct.unpack("<I", d.mem(rf + flagnames.WARP_REG * 4, 4))[0] if rf else None
    print("table hdr count", n, "entsize", es, "bytes", tot, "| search count", c, "| regfile", hex(rf) if rf else None,
          "| warp reg", w, flagnames.decode_map(w) if w else "")
    return n, c
cmd = sys.argv[1]
if cmd == "status": status()
elif cmd == "patch":
    tbl = open(sys.argv[2], "rb").read(); n_new = struct.unpack_from("<H", tbl, 0)[0]
    n, c = status(); assert n == c, "header/count disagree"
    if n == n_new: print("already patched"); sys.exit()
    # the entries the game already has must equal the start of the new table (root off16 were rewritten to LBAs, skip root)
    live = b"".join(d.mem(ENT + o, min(0x8000, n*16 - o)) for o in range(0, n*16, 0x8000)); root = 14; assert len(live) == n*16
    assert live[root*16:] == tbl[16 + root*16:16 + n*16], "live table differs from patched table base"
    write(ENT + n * 16, tbl[16 + n*16:16 + n_new*16])
    write(HDR, tbl[0:8]); write(CNT, struct.pack("<Q", n_new)); status()
elif cmd == "replace":
    import iso
    old, new = iso.Iso(sys.argv[2]), iso.Iso(sys.argv[3])
    tbl = new.read("PKFINFO.TBL"); n_new = struct.unpack_from("<H", tbl, 0)[0]; root = 14
    n, c = status(); assert n == c
    by_lba = {lba: name for name, (lba, sz) in old.files.items()}
    live = d.mem(ENT, root * 16); ent = bytearray(tbl[16:16 + n_new*16])
    for i in range(root):
        assert live[i*16:i*16+8] == ent[i*16:i*16+8], "root key %d differs" % i
        name = by_lba[struct.unpack_from("<I", live, i*16 + 8)[0]]
        struct.pack_into("<I", ent, i*16 + 8, new.files[name][0]); print("  root", i, name, "->", new.files[name][0])
    write(CNT, struct.pack("<Q", min(n, n_new)))          # shrink first so no lookup runs past the new end mid-write
    write(ENT, bytes(ent)); write(HDR, tbl[0:8]); write(CNT, struct.pack("<Q", n_new)); status()
elif cmd == "warp":
    v = flagnames.encode_map(sys.argv[2]); rf = flagnames.register_file(d); assert v is not None and rf
    write(rf + flagnames.WARP_REG * 4, struct.pack("<I", v)); status()
