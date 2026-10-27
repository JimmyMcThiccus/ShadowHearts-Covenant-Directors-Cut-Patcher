"""Splice the Director's Cut Nahash branch into the US CA_02_U (Nelson's boat).
DC 0x2f45..0x2fa9: flag-42 test, SetWorldMapPoint(18,2), boat motions, then SM_00_U (flag 42) or KS_00_U.
US 0x2f7a..0x2fa6 holds the same block minus the test and always jumps to SM_00_U; it becomes `callu NEW 0; jmp 0x2fb4`."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__)); import msc
us_path, dc_path, out_path = sys.argv[1:4]
us = msc.Msc(open(us_path, "rb").read()); dc = msc.Msc(open(dc_path, "rb").read())
DC_LO, DC_HI = 0x2f45, 0x2fa9          # copied range (ends before DC's `jmp 0x2fb7`)
US_LO, US_HI, US_EXIT = 0x2f7a, 0x2fa6, 0x2fb4
# sanity: both blocks look like what we read in the listing
assert us.code[US_HI] == 0x90 and struct.unpack_from("<H", us.code, US_HI+1)[0] == US_EXIT
assert dc.code[DC_HI] == 0x90 and struct.unpack_from("<H", dc.code, DC_HI+1)[0] == 0x2fb7
# nothing may jump into the US bytes we overwrite (except the block start itself)
targets = set()
for ip, (op, ln) in us.insns.items():
    if op in (0x90, 0x91, 0x92): targets.add(struct.unpack_from("<H", us.code, ip+1)[0])
    if op == 0x94:
        tbl = struct.unpack_from("<H", us.code, ip+1)[0]; h = struct.unpack_from("<H", us.code, tbl)[0]; p = tbl+2; kt = (h >> 12) & 7
        for _ in range(h & 0xfff): p += {2: 4, 1: 2}.get(kt, 1); targets.add(struct.unpack_from("<H", us.code, p)[0]); p += 2
        if h & 0x8000: targets.add(struct.unpack_from("<H", us.code, p)[0])
bad = [hex(t) for t in targets if US_LO < t <= US_HI]
assert not bad, bad
sm_off = dict(us.dref)[0x2f9c]; assert us.cstr(sm_off) == b"SM_00_U"
# the copied DC bytes: relocate jumps, re-map the two map-name operands
code = bytearray(us.code)
# Append after the WHOLE code segment.  Its zero tail is not padding: the compiler keeps static variables there (op 0x16 =
# code-segment address; CA_02_U's window flag lives at 0x4940).  Writing the function over it made event 4 (Nelson's boat) hang
# before its first line: the message helper 0x26e saw a non-zero "window open" flag and never created the window.
code_vars = {struct.unpack_from("<H", us.code, ip + 1)[0] for ip, (op, _) in us.insns.items() if op == 0x16}
NEW = len(code); assert all(v + 4 <= NEW for v in code_vars), sorted(map(hex, code_vars))
body = bytearray(dc.code[DC_LO:DC_HI]); base = NEW + 2 - DC_LO
for ip in sorted(i for i in dc.insns if DC_LO <= i < DC_HI):
    op = dc.code[ip]; r = ip - DC_LO
    if op in (0x90, 0x91, 0x92):
        t = struct.unpack_from("<H", dc.code, ip+1)[0]
        assert DC_LO <= t <= DC_HI, hex(t); struct.pack_into("<H", body, r+1, t + base if t < DC_HI else len(body) + NEW + 2)
    assert op != 0x94 and op != 0x16
dc_refs = {ip: dc.cstr(o) for ip, o in dc.dref if DC_LO < ip < DC_HI}
assert sorted(dc_refs.values()) == [b"KS_00_U", b"SM_00_U"], dc_refs
data = bytearray(us.data); ks_off = len(data); data += b"KS_00_U\0"
for ip, s in dc_refs.items(): struct.pack_into("<H", body, ip - DC_LO, sm_off if s == b"SM_00_U" else ks_off)
# GetFieldData(0x36) is a build id: 1 on the DC FIELD.BIN, 2 on the US one (both `li s0,N` in GetFieldData, US 0x004fc5e4).
# The DC test `GetFieldData(54) == 1` means "this is the DC build"; compare with 2 so the skip-if-island-unlocked rule holds here.
assert body[:9] == bytes([0x0a, 54, 6, 6, 0xc2, 0x24, 3, 0x07, 0x74]), body[:9].hex()
body[7] = 0x08                                     # push 1 -> push 2
code += struct.pack("<H", 0) + body + b"\x99"      # u16 locals size, body, ret
code += b"\0" * (-len(code) % 16); data += b"\0" * (-len(data) % 16)
# patch the US call site: callu NEW n=0 ; jmp US_EXIT
patch = bytes([0x1b]) + struct.pack("<H", NEW) + b"\0" + b"\x90" + struct.pack("<H", US_EXIT)
code[US_LO:US_LO+len(patch)] = patch
raw = bytearray(us.raw[:us.code0]) + code + data
struct.pack_into("<H", raw, 8, len(code)//16); struct.pack_into("<H", raw, 0xa, len(data)//16)
if us.reloc_unit:
    struct.pack_into("<H", raw, 0x18, len(raw)//16); raw += us.raw[us.reloc_unit*16:]
out = msc.Msc(bytes(raw))
assert NEW in {struct.unpack_from("<H", out.code, ip+1)[0] for ip, (op, _) in out.insns.items() if op == 0x1b}
names = sorted(out.cstr(o) for ip, o in out.dref if ip > NEW)
print("new function at %#x, %d bytes; map refs inside: %s; code %d -> %d, data %d -> %d" % (NEW, len(body)+3, names, len(us.code), len(code), len(us.data), len(data)))
open(out_path, "wb").write(bytes(raw))
