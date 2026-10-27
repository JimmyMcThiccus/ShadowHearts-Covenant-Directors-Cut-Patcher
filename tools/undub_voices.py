"""UnDub voices outside the cutscenes: replace the US battle sound banks (BTLDATA/SOUND/SE/*.SSE, the voices of every party member
and monster) and the field scene banks (FIELD/SOUND/SE/*.SSE, e.g. *_EVnnB: voices of the in-engine story scenes) with the
Director's Cut ones.  A bank is swapped only when the game can use the DC bank exactly like the US one: the FE
SE-set id must match and every US SE id must exist in the DC bank (the US dropped one voice id from each party member's NNNC bank;
the DC superset still answers every US request).  Four US banks renumbered their WV wave-bank id (006W00, 006W09, 009W08, 226M):
the DC bank keeps the US id.  Banks that are byte-identical, or only on the US disc (190M), stay as they are.
usage: undub_voices.py OUT_D1 OUT_D2   (writes BTLDATA/ and FIELD/SOUND/SE/*.SSE under each, for make_patch's UnDub trees)"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__)); import isoset, sdh

PREFIXES = ("BTLDATA/SOUND/SE/", "FIELD/SOUND/SE/")

def banks(us, dc):
    out, skipped = {}, []
    for p in sorted(x for x in us.tbl if x.startswith(PREFIXES) and x.endswith(".SSE")):
        if p not in dc.tbl: skipped.append((p, "US only")); continue
        ub, db = us.read(p), dc.read(p)
        if ub == db: continue
        fu, fd = sdh.fe(ub), sdh.fe(db)
        if fu is None or fd is None or fu[0] != fd[0] or not {e[0] for e in fu[1]} <= {e[0] for e in fd[1]}:
            skipped.append((p, "SE ids differ")); continue
        db = bytearray(db); wu, wd = sdh.wv(ub), sdh.wv(bytes(db))
        if wu and wd and wu[1] != wd[1]:
            pos = sdh.blocks(bytes(db))["WV"][0] + 10; struct.pack_into("<H", db, pos, wu[1])
            assert sdh.wv(bytes(db))[1] == wu[1]
        out[p] = bytes(db)
    return out, skipped

def main(out1, out2):
    for tag_us, tag_dc, out in (("us1", "dc1", out1), ("us2", "dc2", out2)):
        us, dc = isoset.Disc(tag_us), isoset.Disc(tag_dc)
        got, skipped = banks(us, dc)
        for p, data in got.items():
            f = os.path.join(out, *p.split("/")); os.makedirs(os.path.dirname(f), exist_ok=True); open(f, "wb").write(data)
        n = {k: sum(1 for p in got if p.startswith(k)) for k in PREFIXES}
        print("%s: swapped %s, %d left as US %s" % (tag_us, n, len(skipped), skipped))

if __name__ == "__main__":
    main(*sys.argv[1:3])
