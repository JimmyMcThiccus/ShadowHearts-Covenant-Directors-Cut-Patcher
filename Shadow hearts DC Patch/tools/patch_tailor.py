"""Beautiful Fool (costume 10) support in the US tailor / Change Dress code, ported from the Director's Cut FIELD.BIN.
The DC grows the tailor object's dress-list array at +0x124 from 10 to 11 entries, so every field at or after +0x14c moves by 4
(the object is allocated 0x1c0 bytes in both builds, highest field 0x1b0 -> 0x1b4 still fits), raises the two dress-list loops to 11,
and inserts the dress-10 sketch-book page model as TAILOR.DAT entry 25 (entries 25..30 -> 26..31).
The Change Dress explanation comes from TAILOR.DAT's last msg entry, not CMDMENU, so dress 10's text is added there too.
usage: patch_tailor.py OUT_DIR   (writes FIELD.BIN and SHOP/TAILOR.DAT)"""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(__file__)); import isoset
UB = 0x45ea80
P = json.load(open(os.path.join(os.path.dirname(__file__), "..", "x", "tailor_patches.json")))
FIELD = sorted(a for a, w, b in P["field+4"] if 0x533000 <= a < 0x53c000) + [0x534044, 0x534054, 0x534064, 0x53410c, 0x538010]
INDEX = sorted({a for a, w, b in P["index+1"]} | {0x5385e8})
LIMIT = sorted(a for a, w, b in P["limit"])

FOOL_TEXT = "Sometimes a designer$sacrifices function to$chase impact. Only a$true dandy, ready to$take that risk, may$wear this dress."

def main(out):
    us, dc = isoset.Disc("us1"), isoset.Disc("dc1")
    fb = bytearray(us.iso.read("FIELD.BIN"))
    def get(a): return struct.unpack_from("<I", fb, a - UB)[0]
    def put(a, w): struct.pack_into("<I", fb, a - UB, w)
    for a in FIELD:
        w = get(a); off = w & 0xffff; assert 0x14c <= off <= 0x1b0 and (w >> 21) & 0x1f != 29, hex(a); put(a, w + 4)
    for a in INDEX:
        w = get(a); assert (w >> 16) == 0x2405 and 0x19 <= (w & 0xffff) <= 0x1e, hex(a); put(a, w + 1)
    for a in LIMIT:
        w = get(a); assert (w >> 26) == 0x0a and (w & 0xffff) == 10, hex(a); put(a, w + 1)
    print("FIELD.BIN: %d field offsets, %d TAILOR.DAT indices, %d loop limits" % (len(FIELD), len(INDEX), len(LIMIT)))
    # TAILOR.DAT: {u32 count, u32 total, count x {tag[4], u32 offset}} + data
    def entries(d):
        n = struct.unpack_from("<I", d, 0)[0]; offs = [struct.unpack_from("<I", d, 12 + 8 * i)[0] for i in range(n)] + [len(d)]
        return [(d[8 + 8 * i:12 + 8 * i], d[offs[i]:offs[i + 1]]) for i in range(n)], offs[0]
    ue, uhead = entries(us.read("SHOP/TAILOR.DAT")); de, _ = entries(dc.read("SHOP/TAILOR.DAT"))
    assert len(ue) == 31 and len(de) == 32 and de[25][0] == b"mdl\0" and all(ue[i][1] == de[i][1] for i in range(25))
    new = ue[:25] + [de[25]] + ue[25:]
    # last msg entry = the Change Dress texts {u16 n=22, u16 offs[22], pool}: (reading, explanation) per dress; the US left dress 10's
    # explanation empty.  Same English as the CMDMENU.MDT costume explanation in patch_data.py.
    m = bytearray(new[-1][1]); n = struct.unpack_from("<H", m, 0)[0]; assert new[-1][0] == b"msg\0" and n == 22
    pool = 2 + 2 * n; assert m[pool + struct.unpack_from("<H", m, 2 + 2 * 21)[0]] == 0
    struct.pack_into("<H", m, 2 + 2 * 21, len(m) - pool); m += FOOL_TEXT.encode("ascii") + b"\0"
    new[-1] = (new[-1][0], bytes(m))
    head = 8 + 8 * len(new); first = (head + 0xf) & ~0xf                     # 16-byte aligned like the DC file (first entry 0x110)
    body = bytearray(); offs = []
    for tag, data in new:
        offs.append(first + len(body)); body += data; body += bytes(-len(body) % 16)
    tbl = bytearray(first); struct.pack_into("<II", tbl, 0, len(new), first + len(body))
    for i, (tag, _) in enumerate(new): tbl[8 + 8 * i:12 + 8 * i] = tag; struct.pack_into("<I", tbl, 12 + 8 * i, offs[i])
    tail = bytes(tbl) + bytes(body)
    for path, data in (("FIELD.BIN", fb), ("SHOP/TAILOR.DAT", tail)):
        p = os.path.join(out, *path.split("/")); os.makedirs(os.path.dirname(p) or out, exist_ok=True); open(p, "wb").write(bytes(data))
        print("wrote", path, len(data))
    print("TAILOR.DAT entries", len(new), "first data at", hex(first), "(US first", hex(uhead), ")")

if __name__ == "__main__":
    main(sys.argv[1])
