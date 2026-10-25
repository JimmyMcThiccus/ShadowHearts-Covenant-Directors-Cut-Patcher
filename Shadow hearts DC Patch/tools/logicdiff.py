"""DC-vs-US logic diff over all shared map scripts -> ../x/logic_diff.json; prints the commonest difference kinds in maps with no new DC text."""
import msc, mscnorm, os, json, difflib, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
rs = json.load(open("../x/replace_set.json", encoding="utf-8"))["replace"]
D, U = "../x/dcmsc", "../x/usmsc"; stats = []; kinds = collections.Counter()
for f in sorted(os.listdir(U)):
    if not os.path.exists(os.path.join(D, f)): continue
    try:
        d = msc.Msc(open(os.path.join(D, f), "rb").read()); u = msc.Msc(open(os.path.join(U, f), "rb").read())
        fd, td = mscnorm.tokens(d); fu, tu = mscnorm.tokens(u)
    except Exception as e: continue
    a = [t for fn in fd for _, t in td[fn]]; b = [t for fn in fu for _, t in tu[fn]]
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    dco = sum(i2 - i1 for tag, i1, i2, j1, j2 in ops if tag in ("delete", "replace")); uso = sum(j2 - j1 for tag, i1, i2, j1, j2 in ops if tag in ("insert", "replace"))
    stats.append((f[:-4], len(a), len(b), dco, uso, rs.get(f[:-4], 0)))
    if rs.get(f[:-4], 0) == 0:
        for tag, i1, i2, j1, j2 in ops:
            if tag != "equal": kinds[(" ; ".join(a[i1:i2][:5]), " ; ".join(b[j1:j2][:5]))] += 1
json.dump(stats, open("../x/logic_diff.json", "w"))
nonew = [s for s in stats if s[5] == 0]
print("maps", len(stats), "identical", sum(1 for s in stats if s[3] == s[4] == 0), "| no-new-text maps", len(nonew), "identical", sum(1 for s in nonew if s[3] == s[4] == 0))
print("no-new-text totals: DC-only insns", sum(s[3] for s in nonew), "US-only insns", sum(s[4] for s in nonew))
for k, v in kinds.most_common(30): print(v, "DC:", k[0][:70], "|| US:", k[1][:70])
