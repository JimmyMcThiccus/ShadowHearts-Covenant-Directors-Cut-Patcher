"""Append Director's Cut-only files to a COPY of a US disc image and extend PKFINFO.TBL (test build).
usage: inject.py <us_copy.iso> <dc_disc.iso> <us_other_disc.iso> <out_tbl>"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__)); import iso, pkf
AL = ".0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
def encode(name):
    d = []
    for ch in name.upper():
        if ch in AL and len(d) < 12: d.append(AL.index(ch) + 1)
    d += [0] * (12 - len(d))
    hi, lo = [], []
    for g in range(3):
        u = d[g*4] + d[g*4+1]*40 + d[g*4+2]*1600 + d[g*4+3]*64000
        hi.append(u >> 16); lo.append(u & 0xffff)
    return struct.pack(">4H", hi[0] + hi[1]*40 + hi[2]*1600, lo[0], lo[1], lo[2])
assert pkf.decode(encode("FIELD.BIN")) == "FIELD.BIN" and encode("FIELD.BIN").hex() == "030edd31d9770019"

class Table:
    def __init__(self, raw, isoobj):
        self.raw = bytearray(raw); self.iso = isoobj
        self.n = struct.unpack_from("<H", raw, 0)[0]
        self.ent = [(raw[16+i*16:24+i*16],) + struct.unpack_from("<II", raw, 24+i*16) for i in range(self.n)]
        self.dircount = next((e[2] & 0x7fffffff)//16 for e in self.ent if e[2] & 0x80000000) - 1
    def search(self, start, key):                      # FileIOLib::searchInfo
        for i in range(start, len(self.ent)):
            if start == 0 and self.dircount < i: break
            if self.ent[i][0] == key: return i
        return -1
    def resolve(self, path):                           # FileIOLib::SearchFile -> (lba, size, list) ; size None for dirs
        lst, lba, size = 0, 0, None
        for k, comp in enumerate(path.split("/")):
            i = self.search(lst, encode(comp))
            if i < 0: return None
            key, off, sz = self.ent[i]
            if lst == 0:   # InitPkb replaced root off16 with the disc LBA of NAME.PKB / NAME
                lba = self.iso.files[comp + ("" if "." in comp else ".PKB")][0]
            else: lba += off >> 7
            if sz & 0x80000000: lst += (sz & 0x7fffffff) // 16; size = None
            else: size = sz
        return lba, size, lst

