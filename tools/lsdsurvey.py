"""Compare US and DC cutscenes (LSD) disc by disc: track layout, PCMS size, packet layout.  Writes ../x/lsdsurvey.json"""
import sys, struct, json, hashlib, isoset, lsdtracks
def layout(b):
    n, tps, dur, tr = lsdtracks.tracks(b)
    p = 0x40 + sum(t[5] for t in tr); pk = []
    while p < len(b):
        t, _, seq, nb = struct.unpack_from("<HHII", b, p); pk.append((t, nb)); p += 16 + nb * 16
    pc = [k for k in range(n) if tr[k][1] == "PCMS"]
    return dict(tps=tps, dur=dur, tracks=[(t[1], t[7], t[8].decode("latin1")) for t in tr], pcms=pc,
                pcms_pk=[nb for t, nb in pk if t in pc], pk_hash=hashlib.md5(repr(pk).encode()).hexdigest(), size=len(b),
                pcms_hdr=[b[0x40 + sum(x[5] for x in tr[:k]):0x40 + sum(x[5] for x in tr[:k + 1])].hex() for k in pc])
out = {}
for d in ("1", "2"):
    us, dc = isoset.Disc("us" + d), isoset.Disc("dc" + d)
    names = sorted(p for p in us.tbl if p.endswith(".LSD"))
    for p in names:
        r = {"us": layout(us.read(p))}
        if p in dc.tbl: r["dc"] = layout(dc.read(p))
        out["d%s:%s" % (d, p)] = r
        u, c = r["us"], r.get("dc")
        print(d, p, "US dur %d pcms %s" % (u["dur"], sum(u["pcms_pk"]) * 16 if u["pcms"] else "-"),
              "| DC " + ("dur %d pcms %s same-layout %s" % (c["dur"], sum(c["pcms_pk"]) * 16 if c["pcms"] else "-", c["pk_hash"] == u["pk_hash"]) if c else "missing"), flush=True)
json.dump(out, open("../x/lsdsurvey.json", "w"))
