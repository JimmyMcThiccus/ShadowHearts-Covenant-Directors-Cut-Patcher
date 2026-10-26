"""Readable listing of an MSC around given code offsets.  usage: mscdis.py FILE.MSC ip [ip...]  (prints the enclosing straight-line block)"""
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(__file__)); import msc
sys.stdout.reconfigure(encoding="utf-8")
src = open(r"C:\Users\jamie\Documents\SH2\Sh2 Decomp\sh2-decomp\port\crates\sh2_script\src\opcodes.rs", encoding="utf-8").read()
CF = {int(a, 16): n for a, n in re.findall(r'\(0x([0-9a-f]{2}), "(\w+)"\)', src.split("CField sub-functions")[1].split("];")[0])}
BI = {0xa0: "chain", 0xa1: "callEvent", 0xa2: "callEventDly", 0xa3: "getSysInfo", 0xa4: "setFlag", 0xa5: "clrFlag", 0xa6: "chkFlag",
      0xa7: "reg_clr", 0xaa: "wait", 0xab: "sprintf", 0xac: "get_pad", 0xad: "randomize", 0xae: "rnd", 0xaf: "dprintf"}
def fmt(m, ip):
    op, ln = m.insns[ip]; b = m.code[ip:ip+ln]; a = b[1:]
    if op == 0x15:
        s = m.cstr(struct.unpack_from("<H", a)[0]); return "push &\"%s\"" % s.decode("cp932", "replace")[:50].replace("$", "/")
    if op in (0x0a, 0x0b): return "push %d" % (a[0] if op == 0x0a else -a[0])
    if op in (0x0c, 0x0d): return "push %d" % (struct.unpack_from("<H", a)[0] * (1 if op == 0x0c else -1))
    if op == 0x0e: return "push %#x" % struct.unpack_from("<I", a)[0]
    if op in (5, 6, 7, 8, 9): return "push %d" % {5: -1, 6: 0, 7: 1, 8: 2, 9: 4}[op]
    if op in (0x10, 0x11, 0x12, 0x13): return "push &reg%d[%d]" % ({0x10: 8, 0x11: 16, 0x12: 32, 0x13: 0}[op], a[0])
    if op == 0x14: return "push &reg[%#x]" % struct.unpack_from("<H", a)[0]
    if op == 0x1b: return "callu %#x n=%d" % (struct.unpack_from("<H", a)[0], a[2])
    if op in (0x90, 0x91, 0x92): return {0x90: "jmp", 0x91: "jz", 0x92: "jnz"}[op] + " %#x" % struct.unpack_from("<H", a)[0]
    if op == 0xc2: return "CField.%s n=%d" % (CF.get(a[0], hex(a[0])), a[1])
    if 0xa0 <= op <= 0xaf: return "%s n=%d" % (BI.get(op, hex(op)), a[0])
    if op == 0x98: return "retv"
    if op == 0x99: return "ret"
    return "op%02x %s" % (op, a.hex())
def listing(m, lo, hi):
    for ip in sorted(i for i in m.insns if lo <= i < hi): print("   %05x  %s" % (ip, fmt(m, ip)))
if __name__ == "__main__":
    m = msc.Msc(open(sys.argv[1], "rb").read())
    for t in sys.argv[2:]:
        t = int(t, 16); print("== around %#x" % t); listing(m, t - int(os.environ.get("B", "0x60"), 16), t + int(os.environ.get("A", "0x40"), 16))
