"""Put the Director's Cut "DIRECTOR'S CUT" plate on the US title screen without code changes.
The US mSetupTitleWin draws opening.dat #2..#6 as polys at fixed top-left positions (table @0x46c700, x-0x40) with each texture's own
size.  The DC adds a 6th poly: #21 (256x32) at (184-0x40, 181) = (120, 181), over the rule line #4 at (52-0x40, 173) = (-12, 173).
So #4 is replaced by a taller texture: the rule with the plate composited at the DC spot (an edited plate of another size is centred
on the DC plate's centre x = 248, top kept at y = 181).  Texture = {u16 w,h; u8 8; u8 1; u16 256; u32 0x10; u32 clut_off} + w*h
indices + 256 RGBA (GS alpha 0..0x80, CSM1 order).  usage: insert_plate.py US_OPENING.DAT PLATE.png OUT_OPENING.DAT [preview.png]"""
import sys, struct
from PIL import Image
sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else "."); import menutex
RULE_XY, PLATE_XY, PLATE_CX = (-12, 173), (120, 181), 120 + 128

def encode(im):
    q = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = q.getpalette(rawmode="RGBA")[:1024]; pal += [0] * (1024 - len(pal))
    pal = [tuple(pal[4 * i:4 * i + 4]) for i in range(256)]
    gs = [(r, g, b, (a + 1) // 2) for r, g, b, a in pal]                      # GS alpha: 0x80 = opaque
    filepal = b"".join(bytes(gs[menutex.csm1(i)]) for i in range(256))
    w, h = im.size; pix = q.tobytes(); co = (0x10 + w * h + 15) & ~15
    return struct.pack("<HHBBHII", w, h, 8, 1, 256, 0x10, co) + pix + bytes(co - 0x10 - w * h) + filepal

def main(src, plate_png, out, preview=None):
    b = open(src, "rb").read(); n = struct.unpack_from("<I", b)[0]
    offs = [struct.unpack_from("<I", b, 12 + 8 * i)[0] for i in range(n)] + [len(b)]
    rule = menutex.decode(b, offs[4]); assert rule.size == (464, 16), rule.size
    plate = Image.open(plate_png).convert("RGBA")
    px = PLATE_CX - plate.width // 2 - RULE_XY[0]; py = PLATE_XY[1] - RULE_XY[1]
    assert px >= 0, "plate too wide to centre (max %d px)" % (2 * (PLATE_CX - RULE_XY[0]))
    W, H = max(464, px + plate.width), max(16, py + plate.height)
    canvas = Image.new("RGBA", (W, H)); canvas.alpha_composite(rule, (0, 0)); canvas.alpha_composite(plate, (px, py))
    tex = encode(canvas)
    ents = [b[offs[i]:offs[i + 1]] for i in range(n)]; ents[4] = tex
    head = 8 + 8 * n; body = b""; new_offs = []
    for e in ents:
        new_offs.append(head + len(body)); body += e + bytes(-len(e) % 16)
    tbl = bytearray(b[:head]); struct.pack_into("<II", tbl, 0, n, head + len(body))
    for i in range(n): struct.pack_into("<I", tbl, 12 + 8 * i, new_offs[i])
    data = bytes(tbl) + body; open(out, "wb").write(data)
    back = menutex.decode(data, new_offs[4]); assert back.size == (W, H)
    for i in range(n):
        if i != 4: assert data[new_offs[i]:new_offs[i] + len(ents[i])] == ents[i]
    print("texture #4 -> %dx%d (plate %dx%d at local %d,%d); OPENING.DAT %d -> %d bytes" % (W, H, *plate.size, px, py, len(b), len(data)))
    if preview:   # rough look at the logo area: mist #1, logo #5, new #4 (swirls / emblem left out)
        scr = menutex.decode(b, offs[1]).copy()
        scr.alpha_composite(menutex.decode(b, offs[5]), (100 - 0x40, 124))
        scr.alpha_composite(back, (0, 173), (-RULE_XY[0], 0, min(W, 640 - RULE_XY[0]), H)) if RULE_XY[0] < 0 else scr.alpha_composite(back, RULE_XY)
        scr.save(preview)

if __name__ == "__main__":
    main(*sys.argv[1:])
