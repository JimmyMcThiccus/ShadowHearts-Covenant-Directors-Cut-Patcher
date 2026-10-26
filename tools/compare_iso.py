"""Compare a patched disc image with a reference build, file by file.
usage: compare_iso.py A.iso B.iso US_ORIGINAL.iso DISC [OVERRIDE_DIR]
  The files compared are every file of the original US disc plus the Director's Cut files the patch adds (from release/patchdata.zip),
  each looked up in its own directory the way the game does.  (Walking the patched table directly would also list the appended
  entries under the last directory, which the game never asks for.)
  OVERRIDE_DIR: files whose expected content comes from that tree instead of B (e.g. undub.py output)."""
import sys, os, json, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "release")); sys.path.insert(0, HERE)
import sh2dc_patcher as P, pkf
a_path, b_path, us_path, disc = sys.argv[1:5]; ovr = sys.argv[5] if len(sys.argv) > 5 else None
man = json.loads(zipfile.ZipFile(os.path.join(HERE, "..", "release", "patchdata.zip")).read("manifest.json"))
us = P.Iso(us_path)
paths = sorted({p for p in pkf.load_bytes(us.read_at(*us.files["PKFINFO.TBL"])) if "/" in p} | {p for p, _ in man["discs"][disc]["regular"]["new"]})
a, b = P.Iso(a_path), P.Iso(b_path); ta, tb = P.Table(a), P.Table(b); bad = []
for p in paths:
    o = os.path.join(ovr, *p.split("/")) if ovr else None
    exp = open(o, "rb").read() if o and os.path.exists(o) else P.read_file(b, tb, p)
    if P.read_file(a, ta, p) != exp: bad.append(p)
for n in sorted(us.files):
    if n.endswith(".PKB") or n == "PKFINFO.TBL" or n in (chr(0), chr(1)) or n not in a.files or n not in b.files: continue
    if a.read_at(*a.files[n]) != b.read_at(*b.files[n]): bad.append(n)
print("%d files compared, %d differ" % (len(paths), len(bad)), bad[:20])
