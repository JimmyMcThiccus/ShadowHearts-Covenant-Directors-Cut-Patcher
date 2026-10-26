"""Show DC-only code hunks of a shared map (DC vs US, per function, normalised diff).  usage: hunks.py MAP [min_len]
Prints each DC-only / replaced hunk with DC addresses and readable text, plus the US side for replaced hunks."""
import sys, msc, mscnorm, mscdis, difflib
sys.stdout.reconfigure(encoding="utf-8")
name = sys.argv[1]; minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 3
d = msc.Msc(open("../x/dcmsc/%s.MSC" % name, "rb").read()); u = msc.Msc(open("../x/usmsc/%s.MSC" % name, "rb").read())
fd, td = mscnorm.tokens(d); fu, tu = mscnorm.tokens(u)
A = [(f, ip, t) for f in fd for ip, t in td[f]]; B = [(f, ip, t) for f in fu for ip, t in tu[f]]
ev_d = {f: (k, i) for k, i, f in d.events}; ev_u = {f: (k, i) for k, i, f in u.events}
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x[2] for x in A], [x[2] for x in B], autojunk=False).get_opcodes():
    if tag == "equal" or (i2 - i1) < minlen: continue
    f = A[i1][0]
    print("=== %s DC %d insns @%#x (func %#x %s)  US %d insns @%s" % (tag, i2 - i1, A[i1][1], f, ev_d.get(f, ""), j2 - j1, hex(B[j1][1]) if j1 < len(B) else "-"))
    for k in range(i1, i2): print("   D %05x  %s" % (A[k][1], mscdis.fmt(d, A[k][1])))
    if tag == "replace":
        for k in range(j1, min(j2, j1 + 12)): print("   U %05x  %s" % (B[k][1], mscdis.fmt(u, B[k][1])))
