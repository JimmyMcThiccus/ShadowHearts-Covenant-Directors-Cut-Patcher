"""Print the dialogue of DC code ranges in order (plates + lines) for translating.  usage: scenedump.py MAP lo-hi [lo-hi ...]"""
import sys, msc, json
sys.stdout.reconfigure(encoding="utf-8")
plates = json.load(open("../tr/plates_jp_en.json", encoding="utf-8"))
m = msc.Msc(open("../x/dcmsc/%s.MSC" % sys.argv[1], "rb").read())
for r in sys.argv[2:]:
    lo, hi = (int(x, 16) for x in r.split("-"))
    for ip, o in m.dref:
        if lo <= ip < hi:
            s = m.cstr(o).decode("cp932", "replace")
            if s.startswith("%t0%p4"): print("  [%s]" % plates.get(s[6:], s[6:]), end=" ")
            elif any(ord(c) > 0x7f for c in s): print(s.replace("$", " / "))
