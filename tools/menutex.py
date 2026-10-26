"""Decode a menu-texture bundle (OPENING/OPENING.DAT, WORLDMAP/WMAP*.DAT ...) to PNGs, like sh2_gfx::texture::decode_menu_texture.
Bundle {u32 n, u32 total, n x {tag[4], u32 off}}; texture {u16 w, h; u8 bpp; u8 has_clut; u16 clut_n; u32 pix_off; u32 clut_off}
(offsets relative to the texture), RGBA8 palette with GS alpha (x2), 256-entry palettes in CSM1 order.  usage: menutex.py IN OUT_DIR"""
import sys, os, struct
from PIL import Image
def csm1(i): return (i & ~0x18) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)
def decode(b, off):
    w, h, bpp, has, nc, po, co = struct.unpack_from("<HHBBHII", b, off)
    if not has or bpp not in (4, 8) or not (0 < w <= 2048 and 0 < h <= 2048): return None
    pal = [tuple(b[off + co + 4 * i: off + co + 4 * i + 4]) for i in range(nc)]
    if nc == 256: pal = [pal[csm1(p)] for p in range(256)]
    pal = [(r, g, bl, min(255, a * 2)) for r, g, bl, a in pal]
    n = w * h; px = b[off + po: off + po + (n if bpp == 8 else (n + 1) // 2)]
    idx = px if bpp == 8 else bytes(v for x in px for v in (x & 0xf, x >> 4))[:n]
    im = Image.new("RGBA", (w, h)); im.putdata([pal[i] if i < len(pal) else (0, 0, 0, 0) for i in idx]); return im
if __name__ == "__main__":
    b = open(sys.argv[1], "rb").read(); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    n = struct.unpack_from("<I", b)[0]
    for k in range(n):
        tag = b[8 + 8 * k:12 + 8 * k]; off = struct.unpack_from("<I", b, 12 + 8 * k)[0]
        try: im = decode(b, off)
        except Exception as e: im = None
        print(k, tag, hex(off), im.size if im else "-")
        if im: im.save(os.path.join(out, "%02d_%dx%d.png" % (k, *im.size)))
