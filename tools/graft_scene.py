"""Graft DC hunks into US map scripts with English text.
usage: graft_scene.py SPEC.py OUT_DIR
SPEC.py defines MAPS = {"IN_00_U": [dc hunk start, ...], ...} and EN = [english, ...] in the order of SPEC_jp.json, which this
script keeps (every JP line the grafts need, first-seen order; new lines are appended).  Plates and shared library strings come
from plates_jp_en.json / apply_text.LIB; there is no global-dictionary fallback (grafted lines are DC-only, and the aligner
paired some of them with unrelated US lines).  Missing translations are listed and the scripts are not written."""
import sys, os, json, importlib.util
sys.path.insert(0, os.path.dirname(__file__)); import graft, apply_text
sys.stdout.reconfigure(encoding="utf-8")
TR = os.path.join(os.path.dirname(__file__), "..", "tr")
spec_path, out = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("spec", spec_path); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
jp_path = spec_path.replace(".py", "_jp.json")
order = json.load(open(jp_path, encoding="utf-8")) if os.path.exists(jp_path) else []
plates = json.load(open(os.path.join(TR, "plates_jp_en.json"), encoding="utf-8"))
def text(jp):
    if jp.startswith("%t0%p4") and jp[6:] in plates: return ("%t0%p4" + plates[jp[6:]]).encode("ascii")
    if jp in apply_text.LIB: return apply_text.LIB[jp].encode("ascii")
    if jp not in order: order.append(jp)
    k = order.index(jp)
    return apply_text.wrap(S.EN[k]).encode("ascii") if k < len(S.EN) else b"?"
built = {}
for name, los in S.MAPS.items():
    g = graft.Graft(open("../x/dcmsc/%s.MSC" % name, "rb").read(), open("../x/usmsc/%s.MSC" % name, "rb").read(), text)
    for lo in los:
        if isinstance(lo, tuple) and lo[0] == "event": g.add_event(*lo[1:])     # ("event", kind, id) adds a DC-only event
        elif isinstance(lo, tuple) and lo[0] == "inplace": g.patch_inplace(lo[1])  # ("inplace", dc) takes DC operands
        elif isinstance(lo, tuple) and lo[0] == "replace_event": g.replace_event(*lo[1:])  # whole DC event function
        else: g.add_hunk(lo)
    built[name] = g.build()
    print("==", name, "US", len(g.u.raw), "->", len(built[name]))
    for l in g.log: print("   ", l)
json.dump(order, open(jp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
missing = order[len(S.EN):]
if missing:
    print("untranslated: %d (EN has %d of %d) -> %s" % (len(missing), len(S.EN), len(order), jp_path))
    for t in missing: print("   TODO", t.replace("$", "/"))
    sys.exit(1)
os.makedirs(out, exist_ok=True)
for name, raw in built.items(): open(os.path.join(out, name + ".MSC"), "wb").write(raw)
print("wrote", ", ".join(built), "to", out)
