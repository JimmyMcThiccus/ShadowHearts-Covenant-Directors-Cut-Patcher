"""Translate whole DC scripts by text: speaker plates, the shared-library glossary, a slice's own JP->EN table, then the
global dictionary of official US lines (aligned DC/US pairs).  New strings are appended and the 0x15 operands repointed
(msc.Msc.build); only new English is wrapped to 40 x 3, US lines keep their own breaks.

usage: apply_text.py OUT_DIR SLICE.py MAP [MAP ...]      (SLICE.py: EN list in the order of its TODO json, see ju_en.py)"""
import sys, os, re, json, struct, textwrap, importlib.util
sys.path.insert(0, os.path.dirname(__file__)); import msc
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(__file__); TR = os.path.join(HERE, "..", "tr"); SRC = os.path.join(HERE, "..", "x", "dcmsc")
WIDTH, LINES = 40, 3

LIB = {  # shared field-library strings of the DC script build (item pickups etc., see ks_en.py LIB)
    "の紋章を手に入れた。": " Crest obtained!", "のカードを手に入れた。": " Card obtained!", "を手に入れた。": " obtained!",
    "何も入っていない。": "It's empty.", "後ろからは開けられない。": "It can't be opened from behind.",
    "ＨＰとＭＰが全回復した！": "HP and MP fully restored!", "　": " ", "……": "......",
    # debug-map party presets (SetLocationName), never shown in normal play
    "第二次派遣隊": "Second Expedition", "逃亡者たち": "The Fugitives", "孤狼の掟": "Code of the Lone Wolf",
    "皇女様御一行": "The Princess's Party", "二人きり": "Just the Two of Us", "用心棒と白狼": "Bodyguard & White Wolf",
    "チーム・蔵人": "Team Kurando", "チーム・ウル": "Team Yuri", "桜花起動試験": "Ouka Startup Test", "凸凹コンビ": "The Odd Couple",
    "全員集合！": "Everyone Together!", "修験者たち": "The Ascetics", "人形遣い": "The Puppeteer", "彷徨う踊子": "The Wandering Dancer",
    "ＳＧ団三人組": "The SG Trio", "チャレンジャー": "Challenger",
}

def wrap(text):
    if text.startswith("%") or "$" in text or len(text) <= WIDTH: out = text
    else: out = "$".join(textwrap.wrap(text, WIDTH, break_long_words=False))
    vis = [re.sub(r"%[a-z][0-9]+", "", l) for l in out.split("$")]
    assert max(map(len, vis)) <= WIDTH and len(vis) <= LINES, "does not fit 40x3: %r" % text
    return out

def load_slice(path):
    spec = importlib.util.spec_from_file_location("slice", path); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    todo = json.load(open(path.replace("_en.py", "_todo.json"), encoding="utf-8"))
    assert len(todo) == len(mod.EN), (len(todo), len(mod.EN))
    return {jp: wrap(en) for jp, en in zip(todo, mod.EN)}

def main(out, slice_path, *maps):
    plates = json.load(open(os.path.join(TR, "plates_jp_en.json"), encoding="utf-8"))
    gd = json.load(open(os.path.join(TR, "global_jp_en.json"), encoding="utf-8"))
    mine = load_slice(slice_path) if slice_path != "-" else {}
    os.makedirs(out, exist_ok=True)
    for name in maps:
        m = msc.Msc(open(os.path.join(SRC, name + ".MSC"), "rb").read())
        new, missing, src = {}, set(), {"plate": 0, "lib": 0, "slice": 0, "us": 0}
        for ip, off in m.dref:
            raw = m.cstr(off)
            if not any(c >= 0x80 for c in raw): continue
            jp = raw.decode("cp932", "replace")
            if jp.endswith("\n") or "%d" in jp or "%f" in jp: continue          # debug printf, never on screen
            en = None
            if jp.startswith("%t0%p4") and jp[6:] in plates: en, k = "%t0%p4" + plates[jp[6:]], "plate"
            elif jp in LIB: en, k = LIB[jp], "lib"
            elif jp in mine: en, k = mine[jp], "slice"
            elif jp in gd: en, k = gd[jp], "us"
            if en is None: missing.add(jp); continue
            new[ip] = en.encode("ascii"); src[k] += 1
        built = m.build(new)
        chk = msc.Msc(built); assert set(chk.insns) == set(m.insns)
        for ip, s in new.items(): assert chk.cstr(struct.unpack_from("<H", chk.code, ip)[0]) == s
        open(os.path.join(out, name + ".MSC"), "wb").write(built)
        print("%-8s sites %3d  %s  size %d -> %d" % (name, len(new), src, len(m.raw), len(built)))
        for jp in sorted(missing): print("    MISSING", jp[:60].replace("$", "/"))

if __name__ == "__main__":
    main(*sys.argv[1:])
