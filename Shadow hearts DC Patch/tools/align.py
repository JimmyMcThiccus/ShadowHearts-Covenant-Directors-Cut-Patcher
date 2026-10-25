"""Align the strings of a DC map script with the US script of the same map.

Each script is linearised event by event (event-id order); within a function strings come in address order and every
`callu` target is inlined at its first use.  Strings become tokens: speaker plates `P:<english name>`, dialogue `M`,
other ASCII (motion / map / object names) `X:<text>` (identical in both builds, so they anchor the alignment).
difflib aligns the two token streams; dialogue tokens in equal blocks, and in replace blocks of equal length, are paired.

align(dc_msc, us_msc, plates) -> (pairs {dc data offset: us english bytes}, new [dc data offsets with no US partner])"""
import struct, re, difflib, os, sys
sys.path.insert(0, os.path.dirname(__file__)); import msc

KANA = re.compile(r"[぀-ヿ一-鿿]")

def _funcs(m):
    entries = {m.start} | ({m.end} if m.end != 0xffff else set()) | {f for _, _, f in m.events}
    for ip, (op, ln) in m.insns.items():
        if op == 0x1b: entries.add(struct.unpack_from("<H", m.code, ip + 1)[0])
    return sorted(entries)

def linearize(m, jp, plates, skip=frozenset()):
    ents = _funcs(m); bound = {e: (ents[i + 1] if i + 1 < len(ents) else len(m.code)) for i, e in enumerate(ents)}
    refs = dict(m.dref); seen = set(); out = []
    def tok(off):
        s = m.cstr(off)
        if s in skip: return None                      # shared library strings: translated from a glossary, not aligned
        if re.fullmatch(rb"[ -~]+", s) and not s.startswith(b"%t0%p4"):    # ASCII is classified the same in both builds
            if re.search(rb"[a-z]{2,}", s) and (b" " in s or s.endswith((b".", b"!", b"?"))) and b"%" not in s and b"\n" not in s: return "M"
            return "X:" + s.decode() if s and b"%" not in s else None
        if s.startswith(b"%t0%p4"):
            n = s[6:].decode("cp932", "replace") if jp else s[6:].decode("ascii", "replace")
            return "P:" + (plates.get(n, "?") if jp else n)
        if jp:
            t = s.decode("cp932", "replace")
            if len(KANA.findall(t)) >= 2: return "M"
        else:
            if re.fullmatch(rb"[ -~]+", s) and re.search(rb"[a-z]{2,}", s) and (b" " in s or s.endswith((b".", b"!", b"?"))): return "M"
        if re.fullmatch(rb"[ -~]+", s) and s and b"%" not in s: return "X:" + s.decode()
        return None
    def walk(f):
        if f in seen: return
        seen.add(f)
        for ip in sorted(i for i in m.insns if f <= i < bound.get(f, f + 1)):
            op = m.code[ip]
            if op == 0x15 and ip + 1 in refs:
                t = tok(refs[ip + 1])
                if t: out.append((t, refs[ip + 1]))
            elif op == 0x1b:
                walk(struct.unpack_from("<H", m.code, ip + 1)[0])
    for k, i, f in sorted(m.events, key=lambda e: (e[0], e[1])): walk(f)
    walk(m.start)
    return out

def align(dc_raw, us_raw, plates, skip_dc=frozenset(), skip_us=frozenset()):
    a = msc.Msc(dc_raw); b = msc.Msc(us_raw)
    A = linearize(a, True, plates, skip_dc); B = linearize(b, False, plates, skip_us)
    sm = difflib.SequenceMatcher(None, [t for t, _ in A], [t for t, _ in B], autojunk=False)
    pairs = {}; matched = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for (ta, oa), (tb, ob) in zip(A[i1:i2], B[j1:j2]):
                if ta == "M" and tb == "M":
                    pairs.setdefault(oa, b.cstr(ob)); matched.add(oa)
    new = []
    for t, o in A:
        if t == "M" and o not in matched and o not in new: new.append(o)
    return pairs, new, a
