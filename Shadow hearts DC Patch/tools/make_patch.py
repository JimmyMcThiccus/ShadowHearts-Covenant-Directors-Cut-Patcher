"""Make release/patchdata.zip for sh2dc_patcher.py from the finished builds.
Every output file is stored as a delta against files on the user's own discs (copy ops), so no game data is shipped.
usage: make_patch.py VERSION OVR1 OVR2 FIELD.BIN UNDUB1 UNDUB2 UNDUB_OPENING.DAT OUT.zip
  OVRn          override tree of the regular build for disc n (disc paths, as given to inject2.py)
  FIELD.BIN     the patched root FIELD.BIN (both discs)
  UNDUBn        undub.py output for disc n (LSD/*.LSD, OPENING/DEMO.LSD)
  UNDUB_OPENING the UnDub title texture bundle (OPENING/OPENING.DAT with the UnDub plate)"""
import sys, os, json, zipfile, hashlib, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "release")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sh2dc_patcher as P

ISOS = {"us1": "US-Midway/Shadow Hearts - Covenant (USA) (Disc 1).iso", "us2": "US-Midway/Shadow Hearts - Covenant (USA) (Disc 2).iso",
        "dc1": "Directors cut/Shadow Hearts II - Director's Cut (Japan) (Disc 1).iso", "dc2": "Directors cut/Shadow Hearts II - Director's Cut (Japan) (Disc 2).iso"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
md5 = lambda b: hashlib.md5(b).hexdigest()

def encode_delta(target, sources):
    """Greedy copy/add delta.  Small files: sources indexed by 16-byte blocks every 4 bytes, the target scanned byte by byte where
    nothing matches.  Large files go to _encode_aligned.  Matches are extended as far as they go."""
    if len(target) + sum(map(len, sources)) > (8 << 20):
        return _encode_aligned(target, sources)
    idx = {}
    for s, src in enumerate(sources):
        for off in range(0, len(src) - 15, 4):
            idx.setdefault(src[off:off + 16], (s, off))
    out = bytearray(); lit = bytearray(); p = 0; n = len(target)
    def flush():
        if lit: out.extend(b"A" + struct.pack("<I", len(lit)) + lit); lit.clear()
    while p < n:
        hit = idx.get(target[p:p + 16]) if p + 16 <= n else None
        if hit is None:
            lit.append(target[p]); p += 1; continue
        s, off = hit; src = sources[s]; m = _extend(target, p, src, off)
        flush(); out.extend(b"C" + struct.pack("<BII", s, off, m)); p += m
    flush()
    assert P.apply_delta(bytes(out), sources) == target
    return bytes(out)

def _extend(target, p, src, off):
    """Length of the match target[p:] == src[off:] (at least 16 bytes known to match)."""
    n = len(target); m = 16
    while p + m < n and off + m < len(src):               # extend in 4 KiB steps, then byte by byte
        k = min(4096, n - p - m, len(src) - off - m)
        if target[p + m:p + m + k] == src[off + m:off + m + k]: m += k; continue
        while p + m < n and off + m < len(src) and target[p + m] == src[off + m]: m += 1
        break
    return m

def _encode_aligned(target, sources):
    """Large files (cutscenes): their data sits in 16-byte units, so only 16-byte-aligned blocks are indexed, as a sorted numpy array
    of 64-bit block hashes (about 16 bytes per block instead of a dict entry each)."""
    import numpy as np
    K = np.uint64(0x9E3779B97F4A7C15)
    def hashes(b):
        n = len(b) // 16; v = np.frombuffer(b, "<u8", n * 2).reshape(n, 2); return v[:, 0] * K ^ v[:, 1]
    hs, ids = [], []
    for s, src in enumerate(sources):
        h = hashes(src); hs.append(h); ids.append(np.arange(len(h), dtype=np.int64) * 16 + (s << 40))
    h = np.concatenate(hs); ref = np.concatenate(ids); order = np.argsort(h, kind="stable"); h, ref = h[order], ref[order]
    th = hashes(target); pos = np.minimum(np.searchsorted(h, th), len(h) - 1); hit = h[pos] == th
    cand = np.where(hit, ref[pos], -1).tolist(); del h, ref, order, th, pos, hit
    out = bytearray(); lit = bytearray(); p = 0; n = len(target)
    def flush():
        if lit: out.extend(b"A" + struct.pack("<I", len(lit)) + lit); lit.clear()
    while p < n:
        c = cand[p // 16] if p % 16 == 0 and p + 16 <= n else -1
        if c >= 0:
            s, off = c >> 40, c & ((1 << 40) - 1); src = sources[s]
            if target[p:p + 16] == src[off:off + 16]:
                m = _extend(target, p, src, off); flush(); out.extend(b"C" + struct.pack("<BII", s, off, m)); p += m; continue
        k = 16 - p % 16 if p % 16 else min(16, n - p)
        lit.extend(target[p:p + k]); p += k
    flush()
    assert P.apply_delta(bytes(out), sources) == target
    return bytes(out)

def main(version, ovr1, ovr2, field_bin, und1, und2, und_opening, out_zip):
    man = {"version": version, "discs": {}, "sources": {}}
    z = zipfile.ZipFile(out_zip, "w", zipfile.ZIP_LZMA); nd = [0]
    ovr = {"1": ovr1, "2": ovr2}; und = {"1": und1, "2": und2}
    isos = {k: P.Iso(os.path.join(ROOT, v)) for k, v in ISOS.items()}; tabs = {k: P.Table(v) for k, v in isos.items()}
    def tree(d):       # disc path -> file on disk (read later, by the worker that encodes it)
        out = {}
        for dp, _, ns in os.walk(d):
            for nm in ns:
                full = os.path.join(dp, nm); rel = os.path.relpath(full, d).replace(os.sep, "/")
                if "/" in rel: out[rel] = full
        return out
    jobs, plan = [], {}
    for d in ("1", "2"):
        us, dc, other = "us" + d, "dc" + d, "us" + ("2" if d == "1" else "1")
        dc_paths = _paths(tabs[dc]); us_paths = _paths(tabs[us]) | _paths(tabs[other])
        new_paths = sorted(p for p in dc_paths if p not in us_paths and not p.startswith("LSD/"))
        o = tree(ovr[d]); u = tree(und[d]); log = json.load(open(os.path.join(und[d], "undub_disc%s.json" % d)))
        def job(target_file, refs):
            jobs.append((d, target_file, refs)); return len(jobs) - 1
        new = [[p, job(o[p], ["dc:" + p]) if p in o else job(None, ["dc:" + p])] for p in new_paths]
        rep = {p: job(f, ["us:" + p, "dc:" + p]) for p, f in sorted(o.items()) if p not in new_paths}
        root = [["FIELD.BIN", job(field_bin, ["us:FIELD.BIN"])]]
        undub_rep = dict(rep); resample = []
        undub_rep["OPENING/OPENING.DAT"] = job(und_opening, ["us:OPENING/OPENING.DAT"])
        for p, f in sorted(u.items()):
            if not p.endswith(".LSD"): continue
            if "44.1 kHz" in log.get(p, ""):          # rebuilt on the user's machine (resampling): keep only our subtitle times
                dcb = P.read_file(isos[dc], tabs[dc], p); man["sources"].setdefault(d, {})
                resample.append([p, {"times": _sbtd_times(open(f, "rb").read()), "dc_md5": md5(dcb), "us_md5": md5(P.read_file(isos[us], tabs[us], p))}])
                undub_rep.pop(p, None); continue
            undub_rep[p] = job(f, ["us:" + p, "dc:" + p])
        plan[d] = (new, rep, root, undub_rep, resample)
        man["discs"][d] = {"tables": {"us": md5(isos[us].read_at(*isos[us].files["PKFINFO.TBL"])), "dc": md5(isos[dc].read_at(*isos[dc].files["PKFINFO.TBL"]))}}
        man["sources"].setdefault(d, {})
    # encode in parallel: each worker opens the discs itself and reads one target at a time
    from concurrent.futures import ProcessPoolExecutor
    specs = [None] * len(jobs)
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 1) as ex:
        for k, (spec, delta, srcmd5) in enumerate(ex.map(_job, jobs, chunksize=1)):
            if delta is not None:
                spec["delta"] = "d%05d" % nd[0]; nd[0] += 1; z.writestr(spec["delta"], delta)
            man["sources"][jobs[k][0]].update(srcmd5); specs[k] = spec
            if k % 25 == 0: print("  %d / %d files" % (k + 1, len(jobs)), flush=True)
    for d, (new, rep, root, undub_rep, resample) in plan.items():
        fix = lambda pairs: [[p, specs[j]] for p, j in pairs]
        man["discs"][d]["regular"] = {"new": fix(new), "replace": fix(sorted(rep.items())), "root": fix(root)}
        man["discs"][d]["undub"] = {"new": fix(new), "replace": fix(sorted(undub_rep.items())), "root": fix(root), "resample": resample}
        print("disc", d, ": new", len(new), "replace", len(rep), "/ undub", len(undub_rep), "resample", len(resample))
    z.writestr("manifest.json", json.dumps(man)); z.close()
    print(out_zip, os.path.getsize(out_zip), "bytes")

_W = {}
def _job(j):
    """Worker: build one file's spec -> (spec, delta bytes or None, {source ref: md5})."""
    d, target_file, refs = j
    if not _W: _W.update({k: P.Iso(os.path.join(ROOT, v)) for k, v in ISOS.items()}); _W["t"] = {k: P.Table(v) for k, v in list(_W.items())}
    have = []
    for r in refs:
        tag, name = r.split(":", 1); b = P.read_file(_W[tag + d], _W["t"][tag + d], name)
        if b is not None: have.append((r, b))
    srcmd5 = {r: md5(b) for r, b in have}
    target = open(target_file, "rb").read() if target_file else have[0][1]
    for r, b in have:
        if b == target: return {"copy": r, "md5": md5(target), "size": len(target)}, None, srcmd5
    return {"src": [r for r, _ in have], "md5": md5(target), "size": len(target)}, encode_delta(target, [b for _, b in have]), srcmd5

def _paths(T):
    """Every packed file path in a table (pkf.load walks the directory lists the way the game does)."""
    import pkf
    return {p for p in pkf.load_bytes(bytes(T.raw)) if "/" in p}

def _sbtd_times(lsd):
    n = struct.unpack_from("<H", lsd, 0xa)[0]; p = 0x40; ks = None
    for i in range(n):
        if lsd[p:p + 4] == b"SBTD": ks = i
        p += struct.unpack_from("<H", lsd, p + 0x10)[0] * 16
    if ks is None: return None
    while p < len(lsd):
        t, _, seq, nb = struct.unpack_from("<HHII", lsd, p)
        if t == ks:
            s = p + 16; nl = struct.unpack_from("<h", lsd, s)[0]; lt = struct.unpack_from("<I", lsd, s + 0x14)[0]
            return [list(struct.unpack_from("<ff", lsd, s + lt + i * 0x20 + 0x14)) for i in range(nl)]
        p += 16 + nb * 16

if __name__ == "__main__":
    main(*sys.argv[1:])
