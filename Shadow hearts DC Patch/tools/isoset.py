import sys, os; sys.path.insert(0, os.path.dirname(__file__)); import iso, pkf
R = "C:/Users/jamie/Documents/SH2/Sh2 Decomp"
ISOS = {'dc1': R + "/Directors cut/Shadow Hearts II - Director's Cut (Japan) (Disc 1).iso",
        'dc2': R + "/Directors cut/Shadow Hearts II - Director's Cut (Japan) (Disc 2).iso",
        'us1': R + "/US-Midway/Shadow Hearts - Covenant (USA) (Disc 1).iso",
        'us2': R + "/US-Midway/Shadow Hearts - Covenant (USA) (Disc 2).iso"}
class Disc:
    def __init__(self, tag):
        self.iso = iso.Iso(ISOS[tag]); open(os.path.join(os.path.dirname(__file__), '..', tag, 'PKFINFO.TBL'), 'wb').write(self.iso.read('PKFINFO.TBL'))
        self.tbl = pkf.load(os.path.join(os.path.dirname(__file__), '..', tag, 'PKFINFO.TBL'))
    def read(self, path):
        sz, off = self.tbl[path]
        if '/' not in path: return self.iso.read(path)
        return self.iso.read(path.split('/')[0] + '.PKB', off, sz)
