"""Append Director's Cut-only files to a COPY of a US disc image and extend PKFINFO.TBL (test build).
usage: inject2.py <us_copy.iso> <dc_disc.iso> <us_other_disc.iso> <out_tbl> [overrides_dir]
  overrides_dir/<disc path> replaces that file: DC-only files take the override data, existing US entries are repointed to it.
Existing files never move; new data goes past the old end of the image; PKFINFO.TBL is rewritten at the end and its
root directory record repointed.  Lookups work because FileIOLib::searchInfo scans linearly to the end of the table."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__)); import iso, pkf
from pkfresolve import encode, Table

def main(us_path, dc_path, other_path, out_tbl, ovr_dir=None):
    ovr = {}
    for root, _, names in (os.walk(ovr_dir) if ovr_dir else []):    # overrides_dir mirrors disc paths (FIELD/MPS/X.MSC, COMMON/...)
        for n in names:
            full = os.path.join(root, n); ovr[os.path.relpath(full, ovr_dir).replace(os.sep, "/")] = open(full, "rb").read()
    dc = iso.Iso(dc_path); other = iso.Iso(other_path)
    f = open(us_path, "r+b"); us = iso.Iso(us_path)
    T = Table(us.read("PKFINFO.TBL"), us)
    us_names = set(pkf.load_bytes(us.read("PKFINFO.TBL"))) | set(pkf.load_bytes(other.read("PKFINFO.TBL")))
    dc_tbl = pkf.load_bytes(dc.read("PKFINFO.TBL"))
    new = sorted(p for p in dc_tbl if p not in us_names and not p.startswith("LSD/"))
    f.seek(0, 2); end = f.tell(); assert end % 2048 == 0
    lba = end // 2048; added = []; want = {}

    def put(data):
        nonlocal lba
        at = lba; f.seek(at * 2048); f.write(data + bytes(-len(data) % 2048)); lba += (len(data) + 2047) // 2048
        return at

    for p in new:
        sz, off = dc_tbl[p]
        data = ovr.pop(p) if p in ovr else dc.read(p.split("/")[0] + ".PKB", off, sz)
        d, name = p.rsplit("/", 1)
        base = T.resolve(d); assert base and base[1] is None, p
        at = put(data); want[p] = (at, data)
        added.append((encode(name), (at - base[0]) << 7, len(data)))
    repointed = []
    for p, data in sorted(ovr.items()):             # remaining overrides are existing US files
        d, name = p.rsplit("/", 1); base = T.resolve(d); assert T.resolve(p), "override for unknown file " + p
        i = T.search(base[2], encode(name)); assert i >= 0
        at = put(data); want[p] = (at, data); repointed.append(p)
        T.ent[i] = (T.ent[i][0], (at - base[0]) << 7, len(data))
    T.ent += added
    n = len(T.ent); assert n < 5000
    tbl = struct.pack("<HHI", n, 16, n * 16) + bytes(T.raw[8:16]) + b"".join(k + struct.pack("<II", o, s) for k, o, s in T.ent)
    tbl_lba = put(tbl)
    f.seek(16 * 2048); pvd = bytearray(f.read(2048))
    root_lba, root_size = struct.unpack_from("<I", pvd, 158)[0], struct.unpack_from("<I", pvd, 166)[0]
    f.seek(root_lba * 2048); dr = bytearray(f.read(root_size)); i = 0; done = False
    while i < len(dr):
        L = dr[i]
        if L == 0: i = (i // 2048 + 1) * 2048; continue
        if dr[i+33:i+33+dr[i+32]].split(b";")[0] == b"PKFINFO.TBL":
            struct.pack_into("<I", dr, i+2, tbl_lba); struct.pack_into(">I", dr, i+6, tbl_lba)
            struct.pack_into("<I", dr, i+10, len(tbl)); struct.pack_into(">I", dr, i+14, len(tbl)); done = True
        i += L
    assert done
    f.seek(root_lba * 2048); f.write(dr)
    struct.pack_into("<I", pvd, 80, lba); struct.pack_into(">I", pvd, 84, lba); f.seek(16 * 2048); f.write(pvd)
    f.close(); open(out_tbl, "wb").write(tbl)
    # verify through a fresh parse, the way the game resolves paths
    v = iso.Iso(us_path); T2 = Table(v.read("PKFINFO.TBL"), v); bad = 0
    for p, (at, data) in want.items():
        r = T2.resolve(p); v.f.seek(at * 2048)
        if not r or r[:2] != (at, len(data)) or v.f.read(len(data)) != data: bad += 1; print("BAD", p, r, at)
    for p in ["FIELD/MPS/AP_02_U.MPS", "FIELD/FIELD.DAT", "BTLDATA/CHR/555.BCM", "LSD/N003.LSD", "FIELD/MPS/CA_02_U.MPS"]:
        assert T2.resolve(p) == T.resolve(p) or p in repointed, p
    print("added", len(added), "files; repointed", repointed, "; table entries", n, "; verify failures", bad)
    print("PKFINFO.TBL at LBA", tbl_lba, "size", len(tbl), "; volume now", lba, "sectors")

if __name__ == "__main__":
    main(*sys.argv[1:])
