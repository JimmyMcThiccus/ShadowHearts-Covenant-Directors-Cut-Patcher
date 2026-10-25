"""Normalised instruction streams for comparing DC and US builds of one map script.
tokens(m): per function (entry order: start, end, events by id, then callu targets in first-call order) a list of
(ip, token); addresses (callu / jump targets, data offsets) are replaced by stable symbols, dialogue text by 'TXT'."""
import struct, re, sys, os
sys.path.insert(0, os.path.dirname(__file__)); import msc, mscdis

def order(m):
    ents = [m.start] + ([m.end] if m.end != 0xffff else []) + [f for _, _, f in sorted(m.events, key=lambda e: (e[0], e[1]))]
    seen, out, i = set(), [], 0
    while i < len(ents):
        f = ents[i]; i += 1
        if f in seen: continue
        seen.add(f); out.append(f)
        hi = min([e for e in sorted(set(ents) | set(_targets(m))) if e > f] + [len(m.code)])
        for ip in sorted(x for x in m.insns if f <= x < hi):
            op, ln = m.insns[ip]
            if op == 0x1b: ents.append(struct.unpack_from("<H", m.code, ip + 1)[0])
    return out

def _targets(m):
    if not hasattr(m, "_tg"):
        m._tg = sorted({m.start, *([m.end] if m.end != 0xffff else []), *(f for _, _, f in m.events),
                        *(struct.unpack_from("<H", m.code, ip + 1)[0] for ip, (op, ln) in m.insns.items() if op == 0x1b)})
    return m._tg

def tok(m, ip, fid):
    op, ln = m.insns[ip]; a = m.code[ip + 1:ip + ln]
    if op == 0x15:
        s = m.cstr(struct.unpack_from("<H", a)[0])
        if s.startswith(b"%t0%p4"): return "push &PLATE"
        if s.endswith(b"\n") or b"%d" in s: return "push &DBG"
        ident = re.fullmatch(rb"[A-Za-z0-9_]{1,24}", s or b"-") and (re.search(rb"[0-9_]", s) or s.isupper())
        return "push &" + (s.decode() if ident or re.fullmatch(rb"(%[st0-9p]*)+", s or b"-") else "TXT")
    if op == 0x1b: return "callu n=%d" % a[2]          # no callee id: ids shift when one build adds functions
    if op in (0x90, 0x91, 0x92): return {0x90: "jmp", 0x91: "jz", 0x92: "jnz"}[op]
    if op == 0x94: return "switch"
    if op in (0x16, 0x18, 0x1a): return "op%02x ADDR" % op
    return mscdis.fmt(m, ip)

def strip_dbg(seq):
    """drop debug printf pairs (push &DBG ... dprintf) so they do not count as logic"""
    out = []
    for ip, t in seq:
        if t.startswith("dprintf") and out and out[-1][1] == "push &DBG": out.pop(); continue
        out.append((ip, t))
    return [(ip, t) for ip, t in out if t != "push &DBG"]

def tokens(m):
    fo = order(m); ids = {f: i for i, f in enumerate(fo)}
    tg = _targets(m); out = {}
    for f in fo:
        hi = min([e for e in tg if e > f] + [len(m.code)])
        out[f] = strip_dbg([(ip, tok(m, ip, lambda t: ids.get(t, -1))) for ip in sorted(x for x in m.insns if f <= x < hi)])
    return fo, out
