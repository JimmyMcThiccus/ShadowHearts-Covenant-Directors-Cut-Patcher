"""Replace existing files inside a (patched) disc image: in place when the new data fits the old sectors, else appended past the
end and repointed.  PKFINFO.TBL keeps its entry count, so it is rewritten where it is.  Used by undub.py."""
import struct, iso
from pkfresolve import Table, encode

def _find(T, path):
    """(entry index, file lba) of a disc path, the way FileIOLib::SearchFile walks the table."""
    lst, lba = 0, 0
    for comp in path.split("/"):
        i = T.search(lst, encode(comp)); assert i >= 0, path
        key, off, sz = T.ent[i]
        lba = T.iso.files[comp + ("" if "." in comp else ".PKB")][0] if lst == 0 else lba + (off >> 7)
        if sz & 0x80000000: lst += (sz & 0x7fffffff) // 16
    return i, lba

def apply(path, files):
    I = iso.Iso(path); T = Table(I.read("PKFINFO.TBL"), I); tbl_lba, tbl_size = I.files["PKFINFO.TBL"]
    f = open(path, "r+b"); f.seek(0, 2); end = f.tell() // 2048; inplace = appended = 0
    for p, data in files.items():
        i, lba = _find(T, p); key, off, sz = T.ent[i]
        if (len(data) + 2047) // 2048 <= (sz + 2047) // 2048:
            f.seek(lba * 2048); f.write(data + bytes(-len(data) % 2048)); T.ent[i] = (key, off, len(data)); inplace += 1
        else:
            base = lba - (off >> 7); at = end; f.seek(at * 2048); f.write(data + bytes(-len(data) % 2048))
            end += (len(data) + 2047) // 2048; T.ent[i] = (key, (at - base) << 7, len(data)); appended += 1
    raw = bytearray(T.raw)
    for i, (k, o, s) in enumerate(T.ent): raw[16 + i * 16:32 + i * 16] = k + struct.pack("<II", o, s)
    assert len(raw) == tbl_size; f.seek(tbl_lba * 2048); f.write(raw)
    f.seek(16 * 2048); pvd = bytearray(f.read(2048))
    struct.pack_into("<I", pvd, 80, end); struct.pack_into(">I", pvd, 84, end); f.seek(16 * 2048); f.write(pvd); f.close()
    v = iso.Iso(path); T2 = Table(v.read("PKFINFO.TBL"), v); bad = 0
    for p, data in files.items():
        r = T2.resolve(p); v.f.seek(r[0] * 2048)
        if r[1] != len(data) or v.f.read(len(data)) != data: bad += 1; print("BAD", p)
    print("%s: %d in place, %d appended, verify failures %d" % (path.rsplit("/", 1)[-1], inplace, appended, bad))
    return bad
