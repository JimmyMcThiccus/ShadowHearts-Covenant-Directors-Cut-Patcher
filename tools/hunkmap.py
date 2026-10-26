"""Summarise DC-only hunks of every shared map -> ../x/hunkmap.txt (map, func/event, size, flags/regs set+tested, map jumps, first text)."""
import sys, os, re, struct, msc, mscnorm, mscdis, difflib
sys.stdout.reconfigure(encoding="utf-8")
D, U = "../x/dcmsc", "../x/usmsc"; out = []
for f in sorted(os.listdir(U)):
    if not os.path.exists(os.path.join(D, f)): continue
    try:
        d = msc.Msc(open(os.path.join(D, f), "rb").read()); u = msc.Msc(open(os.path.join(U, f), "rb").read())
        fd, td = mscnorm.tokens(d); fu, tu = mscnorm.tokens(u)
    except Exception: continue
    A = [(fn, ip, t) for fn in fd for ip, t in td[fn]]; B = [t for fn in fu for _, t in tu[fn]]
    ev = {fn: "ev%d.%d" % (k, i) for k, i, fn in d.events}; ev[d.start] = "start"
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [x[2] for x in A], B, autojunk=False).get_opcodes():
        if tag not in ("delete", "replace") or i2 - i1 < 6: continue
        lines = [mscdis.fmt(d, A[k][1]) for k in range(i1, i2)]
        txt = " ".join(lines)
        sets = re.findall(r"push (\d+) setFlag", txt.replace("\n", " ").replace("  ", " ")) 
        # flags: "push N" immediately followed by setFlag / chkFlag / clrFlag
        fl = {"set": [], "chk": [], "clr": []}
        for k in range(1, len(lines)):
            for key, nm in (("set", "setFlag"), ("chk", "chkFlag"), ("clr", "clrFlag")):
                if lines[k].startswith(nm) and lines[k-1].startswith("push ") and lines[k-1][5:].lstrip("-").isdigit(): fl[key].append(int(lines[k-1][5:]))
        regs = sorted(set(re.findall(r"reg\[(0x[0-9a-f]+)\]", txt)))
        maps = sorted(set(re.findall(r'push &"([A-Z]{2}_[0-9A-Z]{2}_[A-Z0-9]{1,2}|_QUIZ)"', txt)))
        jp = [l[7:-1] for l in lines if l.startswith('push &"') and re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", l) and "%t0%p4" not in l]
        out.append("%-8s %-6s %-10s DC %4d US %4d | set %s chk %s clr %s | regs %s | maps %s | %s" % (
            f[:-4], tag[:3], ev.get(A[i1][0], "f%#x" % A[i1][0]), i2 - i1, j2 - j1, fl["set"][:6], fl["chk"][:6], fl["clr"][:4], regs[:5], maps[:5], (jp[0][:30] if jp else "")))
open("../x/hunkmap.txt", "w", encoding="utf-8").write("\n".join(out))
print(len(out), "hunks")
