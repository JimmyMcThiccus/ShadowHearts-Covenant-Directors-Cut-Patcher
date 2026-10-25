"""Apply an English table to DC scripts: append translated strings to each MSC's data segment and repoint the 0x15 operands.
usage: apply_tr.py TABLE.py SRC_DIR OUT_DIR"""
import sys, os, re, struct, importlib.util, textwrap
sys.path.insert(0, os.path.dirname(__file__)); import msc
sys.stdout.reconfigure(encoding="utf-8")
WIDTH, LINES = 40, 3

def wrap(text):
    if text.startswith("%") or "$" in text or len(text) <= WIDTH:
        out = text
    else:
        out = "$".join(textwrap.wrap(text, WIDTH, break_long_words=False))
    vis = [re.sub(r"%[a-z][0-9]+", "", l) for l in out.split("$")]
    assert max(map(len, vis)) <= WIDTH and len(vis) <= LINES, "does not fit 40x3: %r" % text
    return out.encode("ascii")

def caption_sites(m):
    """Per typewriter call (callu 0x6246): the 0x15 operand offsets pushed after its count argument."""
    calls = [ip for ip, (op, ln) in sorted(m.insns.items()) if op == 0x1b and struct.unpack_from("<H", m.code, ip+1)[0] == 0x6246]
    out = []; prev = 0
    for c in calls:
        sites = [ip for ip, o in m.dref if prev < ip < c]
        out.append(sites[-(m.code[c+3] - 1):]); prev = c
    return out

def main(table, src, dst):
    spec = importlib.util.spec_from_file_location("tab", table); tab = importlib.util.module_from_spec(spec); spec.loader.exec_module(tab)
    os.makedirs(dst, exist_ok=True)
    for name, tr in tab.KS.items():
        m = msc.Msc(open(os.path.join(src, name + ".MSC"), "rb").read())
        new = {}; missing = set()
        cap = caption_sites(m) if name == "KS_00_U" else []
        cap_ops = {}
        for line_sites, chunks in zip(cap, getattr(tab, "CAPTION_LINES", [])):
            assert len(line_sites) == len(chunks), (name, len(line_sites), len(chunks))
            for ip, ch in zip(line_sites, chunks): cap_ops[ip] = ch.encode("ascii")
        for ip, off in m.dref:
            if ip in cap_ops: new[ip] = cap_ops[ip]; continue
            s = m.cstr(off)
            if off in tr: new[ip] = wrap(tr[off])
            elif any(c >= 0x80 for c in s): missing.add((off, s.decode("cp932", "replace")))
        out = m.build(new)
        if cap and getattr(tab, "CAPTION_WIDTH", None):
            # caption windows: callu 0x2564(id, x, y, cols, rows, kind) before each typewriter line; 12 cols fit 12 kana,
            # not ~32 English chars (seen live: "Mediterranean" clipped).  Widen the `push cols` operand in place.
            out = bytearray(out); ins = sorted(m.insns)
            for c in [ip for ip in ins if m.code[ip] == 0x1b and struct.unpack_from("<H", m.code, ip+1)[0] == 0x2564 and ip < cap[-1][-1] and ip > cap[0][0] - 0x40]:
                k = ins.index(c); args = ins[k-6:k]
                assert m.code[args[3]] == 0x0a and m.code[args[3]+1] == 12, hex(c)
                out[m.code0 + args[3] + 1] = tab.CAPTION_WIDTH
            out = bytes(out)
        chk = msc.Msc(out)                       # re-parse: same instructions, every repointed string reads back
        assert set(chk.insns) == set(m.insns)
        for ip, s in new.items(): assert chk.cstr(struct.unpack_from("<H", chk.code, ip)[0]) == s
        open(os.path.join(dst, name + ".MSC"), "wb").write(out)
        print("%s: %d sites repointed, data %d -> %d bytes, size %d -> %d" % (name, len(new), len(m.data), len(chk.data), len(m.raw), len(out)))
        for off, s in sorted(missing): print("   untranslated %04x %s" % (off, s))

if __name__ == "__main__":
    main(*sys.argv[1:4])
