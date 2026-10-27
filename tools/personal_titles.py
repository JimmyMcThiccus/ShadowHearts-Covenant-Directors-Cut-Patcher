"""Title images for Lenny's and Veronica's special-skill pages (Personal screen, top left).

PERSONAL.MSD attach 21 holds the title textures of the special pages: 0..5 Manifestations, Marionette, Album, Muscle Arts,
Support Fire, White Magic, then 6 / 7 for Iron Claw / Punish.  The DC draws its own calligraphy there; the US left copies of
"Soul Energy" and "Game Over" in slots 6 / 7.  This builds "Iron Claw" and "Punish" in the US title style from letters cut out of
other US title textures (each letter = one body blob of light pixels plus its own outline and drop shadow), read from the user's
US disc at build time, so no game art is stored here.  Textures: 128x32, 8 bpp, 256-colour palette (`insert_plate.encode`).
usage: personal_titles.py OUT_DIR   (writes the two PNGs, for checking)"""
import sys, os, struct
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__)); import isoset, msdfile, menutex
from insert_plate import encode

SOURCES = {"PLIST": ("MENU/MSD/PLIST.MSD", [0]), "CREST": ("MENU/MSD/CREST.MSD", [0]), "FORM": ("MENU/MSD/FORM.MSD", [0]),
           "WOLF": ("MENU/MSD/PERSONAL.MSD", [16, 0]), "MARIO": ("MENU/MSD/PERSONAL.MSD", [21, 1]),
           "MUSCLE": ("MENU/MSD/PERSONAL.MSD", [21, 3]), "SUPPORT": ("MENU/MSD/PERSONAL.MSD", [21, 4])}
# letter -> (source title, body blobs left to right, optional right edge in px)
LETTERS = {"I": ("PLIST", [0]), "r": ("SUPPORT", [7]), "o": ("MARIO", [4]), "n": ("MARIO", [5]), "C": ("CREST", [0]),
           "a": ("FORM", [1]), "P": ("FORM", [0]), "u": ("MUSCLE", [1]), "i": ("SUPPORT", [5, 6]), "s": ("MUSCLE", [2]),
           "h": ("CREST", [4])}
EXPECT = {"PLIST": "Inventory", "CREST": "Crest Change", "FORM": "Party Members", "WOLF": "Wolf Bout", "MARIO": "Marionette",
          "MUSCLE": "Muscle Arts", "SUPPORT": "Support Fire"}

def nested(b, chain):
    for k in chain:
        ao, att = msdfile.attaches(b); o, i, sz = att[k]; b = b[o:o + sz]
    return b

class Titles:
    def __init__(self, disc=None):
        d = disc or isoset.Disc("us1"); self.src = {}
        for k, (path, chain) in SOURCES.items():
            self.src[k] = np.array(menutex.decode(nested(d.read(path), chain), 0)).astype(int)

    def blobs(self, k):
        a = self.src[k]; body = (a[:, :, :3].mean(2) > 110) & (a[:, :, 3] > 128)
        lab, n = ndimage.label(body, structure=np.ones((3, 3))); objs = ndimage.find_objects(lab)
        return a, lab, [i + 1 for i in sorted(range(n), key=lambda i: objs[i][1].start)]

    def glyph(self, k, idx, xmax=None):
        a, lab, ids = self.blobs(k)
        mine = np.isin(lab, [ids[i] for i in idx])
        if xmax is not None: mine[:, xmax + 1:] = False
        others = (lab > 0) & ~mine
        reg = ndimage.binary_dilation(mine, np.ones((3, 3)))
        for dy, dx in ((1, 1), (2, 2), (1, 2), (2, 1)): reg = reg | np.roll(np.roll(reg, dy, 0), dx, 1)
        reg &= ~others
        if others.any():                                # outline / shadow pixels belong to the nearer letter body (the shadow falls
            d_mine = ndimage.distance_transform_edt(~mine)            # down-right, so measure from the body shifted that way too)
            d_other = ndimage.distance_transform_edt(~others)
            sh = np.zeros_like(mine); sh[1:, 1:] = mine[:-1, :-1]; d_mine = np.minimum(d_mine, ndimage.distance_transform_edt(~sh))
            reg &= d_mine < d_other
        xs = np.where(mine.any(0))[0]
        reg[:, xs.max() + 4:] = False                   # nothing past the letter's own outline + 2 px shadow
        out = a.astype(np.uint8).copy(); out[~reg] = 0
        return Image.fromarray(out), int(xs.min()), int(xs.max())

    def letter(self, ch):
        if ch == "l":                                   # the l of "Muscle": the part of the "le" blob under its ascender
            a, lab, ids = self.blobs("MUSCLE"); asc = np.where((lab == ids[4])[6:10].any(0))[0]
            return self.glyph("MUSCLE", [4], xmax=int(asc.max()))
        if ch == "w":                                   # no US title has a lowercase w: the W of "Wolf Bout" at x-height
            im, l, r = self.glyph("WOLF", [0]); W = im.crop((l - 1, 4, r + 4, 27))
            sw = W.resize((int(W.width * 0.72), int(W.height * 0.72)), Image.LANCZOS)
            out = Image.new("RGBA", (128, 32), (0, 0, 0, 0)); out.alpha_composite(sw, (l - 1, 27 - sw.height))
            return out, l, l - 1 + sw.width - 4
        return self.glyph(*LETTERS[ch])

    def word(self, text, space=5):
        out = Image.new("RGBA", (128, 32), (0, 0, 0, 0)); x = 2
        for ch in text:
            if ch == " ": x += space; continue
            im, l, r = self.letter(ch); out.alpha_composite(im, (x - l, 0)) if x >= l else out.alpha_composite(im.crop((l - x, 0, 128, 32)), (0, 0))
            x += r - l + 1
        assert x < 124, (text, x)
        a = np.array(out); lab, n = ndimage.label(a[:, :, 3] > 0, structure=np.ones((3, 3)))   # drop specks left by neighbours' outlines
        for i, sl in enumerate(ndimage.find_objects(lab)):
            if (lab[sl] == i + 1).sum() < 8: a[lab == i + 1] = 0
        return Image.fromarray(a)

def textures(disc=None):
    """{texture slot in PERSONAL.MSD attach 21: encoded texture bytes}"""
    t = Titles(disc); return {6: encode(t.word("Iron Claw")), 7: encode(t.word("Punish"))}

def apply(per, disc=None):
    """write the two textures into PERSONAL.MSD attach 21 slots 6 / 7 in place (same size: 128x32 8 bpp)"""
    ao, att = msdfile.attaches(bytes(per)); o, i, sz = att[21]; sub = bytes(per[o:o + sz])
    sao, satt = msdfile.attaches(sub)
    for slot, tex in textures(disc).items():
        so, si, ss = satt[slot]; old = sub[so:so + ss]
        assert struct.unpack_from("<HHBB", old) == (128, 32, 8, 1) and len(tex) <= ss, (slot, len(tex), ss)
        per[o + so:o + so + len(tex)] = tex

if __name__ == "__main__":
    t = Titles(); os.makedirs(sys.argv[1], exist_ok=True)
    for name in ("Iron Claw", "Punish"): t.word(name).save(os.path.join(sys.argv[1], name.replace(" ", "_") + ".png"))
