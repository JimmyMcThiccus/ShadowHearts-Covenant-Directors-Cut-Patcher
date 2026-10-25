"""Graft Director's Cut code blocks into a US map script (shared maps whose US logic must be kept).

For each selected DC-only block (a 'delete' hunk of the normalised DC/US diff, see mscnorm/hunks.py) the insertion point X in
the US code is the US instruction the diff pairs with the first DC instruction after the block.  At X the US bytes (whole
instructions, >= 3 bytes) are replaced by `jmp DETOUR`; the detour (appended to the code segment) holds the DC block, then a
verbatim copy of the overwritten US instructions ("replay"), then `jmp` back.  Detours run in the caller's frame, so locals
stay valid.  US jumps into the overwritten bytes are moved into the replay; US jumps to X itself keep going through the
detour only when their DC twin targets the block start (else they skip it, like the DC).

Inside copied DC code: jumps to the block's own bytes stay inside, a jump to the block end goes to the replay, other jumps use
the DC->US instruction map; `callu`/code addresses use the US function the DC call sites line up with (or a copy of the DC
function, recursively); bss operands are mapped from paired instructions; strings are re-added to the US data segment through
`text(jp) -> bytes` (raises KeyError for an untranslated line, so callers can collect a todo list).

usage (library):  g = Graft(dc_raw, us_raw, text); g.add_hunk(dc_lo, dc_hi); raw = g.build()"""
import struct, sys, os, difflib
sys.path.insert(0, os.path.dirname(__file__)); import msc, mscnorm, mscdis

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
JUMPS = (0x90, 0x91, 0x92)

def switch_table(code, tbl):
    """-> list of (byte offset of a target u16, target) and the table end, for an op94 table at code offset tbl"""
    h = u16(code, tbl); kt = (h >> 12) & 7; p = tbl + 2; out = []
    for _ in range(h & 0xfff):
        p += {2: 4, 1: 2}.get(kt, 1); out.append((p, u16(code, p))); p += 2
    if h & 0x8000: out.append((p, u16(code, p))); p += 2
    return out, p

class Graft:
    def __init__(self, dc_raw, us_raw, text):
        self.d = d = msc.Msc(dc_raw); self.u = u = msc.Msc(us_raw); self.text = text
        fd, td = mscnorm.tokens(d); fu, tu = mscnorm.tokens(u)
        self.A = A = [(f, ip, t) for f in fd for ip, t in td[f]]; self.B = B = [(f, ip, t) for f in fu for ip, t in tu[f]]
        self.ops = difflib.SequenceMatcher(None, [x[2] for x in A], [x[2] for x in B], autojunk=False).get_opcodes()
        self.ipmap, self.rev, calls, bss = {}, {}, {}, {}
        for tag, i1, i2, j1, j2 in self.ops:
            if tag != "equal": continue
            for (fa, ia, ta), (fb, ib, tb) in zip(A[i1:i2], B[j1:j2]):
                self.ipmap[ia] = ib; self.rev[ib] = ia
                oa, ob = d.code[ia], u.code[ib]
                if oa == ob and oa in (0x1b, 0x16): calls.setdefault(u16(d.code, ia + 1), set()).add(u16(u.code, ib + 1))
                if oa == ob == 0x18: bss.setdefault(u16(d.code, ia + 1), set()).add(u16(u.code, ib + 1))
        self.funcmap = {k: next(iter(v)) for k, v in calls.items() if len(v) == 1}
        # strings at paired positions (same instruction stream): copied DC code reuses the official US text for them
        self.pairs = {}
        for tag, i1, i2, j1, j2 in self.ops:
            if tag != "equal": continue
            for (_, ia, ta), (_, ib, tb) in zip(A[i1:i2], B[j1:j2]):
                if d.code[ia] == 0x15 and u.code[ib] == 0x15:
                    sa, sb = d.cstr(u16(d.code, ia + 1)), u.cstr(u16(u.code, ib + 1))
                    if any(c >= 0x80 for c in sa) and not any(c >= 0x80 for c in sb): self.pairs.setdefault(sa, sb)
        # fallback for functions no paired call site names: identical normalised body (callee ids ignored)
        import re
        body = lambda toks: tuple(re.sub(r"callu F-?\d+", "callu", t) for _, t in toks)
        us_bodies = {}
        for f in fu: us_bodies.setdefault(body(tu[f]), []).append(f)
        for f in fd:
            if f not in self.funcmap and len(us_bodies.get(body(td[f]), [])) == 1 and len(td[f]) > 2:
                self.funcmap[f] = us_bodies[body(td[f])][0]
        self.bssmap = {k: next(iter(v)) for k, v in bss.items() if len(v) == 1}
        self.dc_entries = sorted(set(mscnorm._targets(d)))
        self.code = bytearray(u.code); self.data = bytearray(u.data)
        self.copied = {}; self.hunks = []; self.strcache = {}; self.log = []; self.events = []; self.replaced = []
        self.us_jump_sites = self._jump_sites(u)

    # ---------- helpers
    def _jump_sites(self, m):
        """[(byte offset of the u16 target, target, kind)] for every code-address operand in m"""
        out = []
        for ip, (op, ln) in m.insns.items():
            if op in JUMPS: out.append((ip + 1, u16(m.code, ip + 1), "jump", (ip, None)))
            elif op == 0x16: out.append((ip + 1, u16(m.code, ip + 1), "code", (ip, None)))
            elif op == 0x94:
                for k, (p, t) in enumerate(switch_table(m.code, u16(m.code, ip + 1))[0]): out.append((p, t, "switch", (ip, k)))
        return out

    def _alloc(self, size, align=2):
        while len(self.code) % align: self.code.append(0)
        at = len(self.code); self.code += bytes(size); return at

    def _string(self, off):
        raw = self.d.cstr(off)
        if raw not in self.strcache:
            s = raw if not any(c >= 0x80 for c in raw) else self.pairs.get(raw) or self.text(raw.decode("cp932"))
            self.strcache[raw] = len(self.data); self.data += s + b"\0"
            assert len(self.data) < 0x10000
        return self.strcache[raw]

    def _end_of(self, f):
        later = [e for e in self.dc_entries if e > f]
        return later[0] if later else len(self.d.code)

    def func(self, f):
        """US address to call for DC function f (mapped, or copied from the DC)"""
        if f in self.funcmap: return self.funcmap[f]
        if f in self.copied: return self.copied[f]
        lo, hi = f, self._end_of(f)
        at = self._alloc(hi - lo); self.copied[f] = at
        self.log.append("copied DC function %#x (%d bytes) -> %#x" % (f, hi - lo, at))
        def ext(t):
            raise AssertionError("DC function %#x jumps outside itself to %#x" % (f, t))
        self._emit(lo, hi, at, ext)
        return at

    def _emit(self, lo, hi, at, external):
        """copy DC bytes [lo, hi) to US code at `at`, relocating every operand"""
        d = self.d; body = bytearray(d.code[lo:hi])
        res = lambda t: at + (t - lo) if lo <= t < hi else external(t)
        for ip in sorted(i for i in d.insns if lo <= i < hi):
            op, ln = d.insns[ip]; r = ip - lo
            assert ip + ln <= hi, "instruction crosses the copied range at %#x" % ip
            if op in JUMPS: struct.pack_into("<H", body, r + 1, res(u16(d.code, ip + 1)))
            elif op == 0x1b: struct.pack_into("<H", body, r + 1, self.func(u16(d.code, ip + 1)))
            elif op == 0x16:                                # code address: a function, a label, or a static variable in the code segment
                t = u16(d.code, ip + 1)
                if t in self.funcmap: v = self.funcmap[t]
                elif t in self.dc_entries: v = self.func(t)
                elif lo <= t < hi: v = res(t)
                else: raise AssertionError("unmapped code address %#x (op16 at DC %#x)" % (t, ip))
                struct.pack_into("<H", body, r + 1, v)
            elif op == 0x15: struct.pack_into("<H", body, r + 1, self._string(u16(d.code, ip + 1)))
            elif op == 0x18:
                t = u16(d.code, ip + 1); assert t in self.bssmap, "unmapped bss operand %#x at DC %#x" % (t, ip)
                struct.pack_into("<H", body, r + 1, self.bssmap[t])
            elif op == 0x94:
                tbl = u16(d.code, ip + 1); assert lo <= tbl < hi, "switch table outside the copied range"
                struct.pack_into("<H", body, r + 1, at + tbl - lo)
                for p, t in switch_table(d.code, tbl)[0]: struct.pack_into("<H", body, p - lo, res(t))
            elif op == 0x8d: raise AssertionError("op8d in copied code at DC %#x" % ip)
        self.code[at:at + len(body)] = body

    # ---------- hunks
    def hunk_for(self, dc_lo):
        for tag, i1, i2, j1, j2 in self.ops:
            if tag in ("delete", "replace") and self.A[i1][1] == dc_lo: return tag, i1, i2, j1, j2
        raise KeyError("no delete/replace hunk starts at DC %#x" % dc_lo)

    def add_hunk(self, dc_lo):
        """delete hunk: the DC block runs before US X.  replace hunk: it runs instead of the US instructions [X, Y)."""
        tag, i1, i2, j1, j2 = self.hunk_for(dc_lo)
        last = self.A[i2 - 1][1]; hi = last + self.d.insns[last][1]
        assert self.A[i2][1] == hi, "hunk end %#x is not followed by the paired instruction (%#x)" % (hi, self.A[i2][1])
        X, Y = self.B[j1][1], self.B[j2][1]; assert self.ipmap[hi] == Y
        if tag == "replace":
            assert self.B[j2 - 1][0] == self.B[j1][0], "replaced US range crosses a function"
            self.log.append("replace: US %#x-%#x (%s) gives way to DC %#x-%#x" % (X, Y, "; ".join(mscdis.fmt(self.u, b[1]) for b in self.B[j1:j2]), dc_lo, hi))
        self.hunks.append({"lo": dc_lo, "hi": hi, "X": X, "Y": Y})

    def patch_inplace(self, dc_lo):
        """a replace hunk whose DC and US instructions pair up with equal opcodes and sizes: take the DC operands in place
        (string operands are re-added to the US data).  Used for retargeted exits, entry numbers, positions."""
        tag, i1, i2, j1, j2 = self.hunk_for(dc_lo); assert tag == "replace" and i2 - i1 == j2 - j1, "not a 1:1 replace"
        for (_, da, _), (_, ua, _) in zip(self.A[i1:i2], self.B[j1:j2]):
            op, ln = self.d.insns[da]; uop, uln = self.u.insns[ua]
            const = lambda o: 0x05 <= o <= 0x0f                     # plain constant pushes may swap opcode (push 1 / push 2)
            assert ln == uln and (op == uop or (const(op) and const(uop))), "size/opcode differ at DC %#x / US %#x" % (da, ua)
            assert op not in JUMPS + (0x1b, 0x16, 0x18, 0x94), "operand kind needs relocation"
            before = mscdis.fmt(self.u, ua)
            if op == 0x15: struct.pack_into("<H", self.code, ua + 1, self._string(u16(self.d.code, da + 1)))
            else: self.code[ua:ua + ln] = self.d.code[da:da + ln]
            self.log.append("in place US %#x: %s -> %s" % (ua, before, mscdis.fmt(self.d, da)))

    def replace_event(self, kind, eid):
        """point the US event (kind, eid) at a copy of the DC event function (for events the DC rewrote mid-expression)"""
        f = [fn for k, i, fn in self.d.events if (k, i) == (kind, eid)]; assert f, "no DC event %s" % ((kind, eid),)
        assert [1 for k, i, fn in self.u.events if (k, i) == (kind, eid)], "US has no event %s" % ((kind, eid),)
        self.replaced.append((kind, eid, f[0]))

    def add_event(self, kind, eid):
        """add the DC-only event (kind, eid) to the US event table, pointing at a copy of its DC function"""
        f = [fn for k, i, fn in self.d.events if (k, i) == (kind, eid)]; assert f, "no DC event %s" % ((kind, eid),)
        assert not [1 for k, i, fn in self.u.events if (k, i) == (kind, eid)], "US already has event %s" % ((kind, eid),)
        self.events.append((kind, eid, f[0]))

    def _patch_site(self, X, Y):
        """end of the overwritten US bytes: whole instructions from X, at least 3 bytes, at least up to Y, and ending on a
        statement boundary.  The VM (CScript::JobExec) evaluates RPN until a 0x90-0x9f statement or an op01 marker and then
        resets the operand stack (sp = frame), so the jump back from a detour must land where the stack is empty anyway:
        right after a statement opcode (jmp/jz/jnz/switch/ret) or on an op01.  Jumping back mid-expression dropped pushed
        arguments (IN_00_U: the speaker plate before callu 0x26e -> garbage pointer -> crash)."""
        u = self.u; ips = sorted(u.insns); k = ips.index(X); end = X; last = None
        while not (end - X >= 3 and end >= Y and ((last is not None and 0x90 <= last <= 0x9f) or u.code[end] == 0x01)):
            assert ips[k] == end, "replay runs into unreachable bytes at %#x" % end
            last = u.code[end]; end += u.insns[end][1]; k += 1
        return end

    def build(self):
        u = self.u
        for h in self.hunks:
            h["end"] = self._patch_site(h["X"], h["Y"])
            h["at"] = self._alloc(h["hi"] - h["lo"], 1)
            h["replay"] = self._alloc(h["end"] - h["Y"], 1)
            h["back"] = self._alloc(3, 1)
        by_lo = {h["lo"]: h for h in self.hunks}; by_hi = {h["hi"]: h for h in self.hunks}
        def ext(t):
            for h in self.hunks:
                if h["lo"] <= t < h["hi"]: return h["at"] + t - h["lo"]
            if t in by_hi: return by_hi[t]["replay"]
            assert t in self.ipmap, "DC jump target %#x has no US partner" % t
            return self.ipmap[t]
        for h in self.hunks:
            self._emit(h["lo"], h["hi"], h["at"], ext)
            # replay: the overwritten US bytes, jump/switch operands relocated into the replay when they point inside it
            rb = bytearray(u.code[h["Y"]:h["end"]])
            for ip in sorted(i for i in u.insns if h["Y"] <= i < h["end"]):
                op = u.code[ip]
                if op in JUMPS or op == 0x16:
                    t = u16(u.code, ip + 1)
                    assert not h["X"] <= t < h["Y"], "replayed jump into the replaced US range"
                    if h["Y"] <= t < h["end"]: struct.pack_into("<H", rb, ip - h["Y"] + 1, h["replay"] + t - h["Y"])
                if op == 0x94:                                      # a switch keeps its (absolute) table if the table stays put
                    tbl = u16(u.code, ip + 1); assert not h["X"] <= tbl < h["end"], "switch table inside the replay"
                    assert all(not h["X"] <= t < h["end"] for _, t in switch_table(u.code, tbl)[0]), "switch into the replay"
            self.code[h["replay"]:h["replay"] + len(rb)] = rb
            self.code[h["back"]:h["back"] + 3] = bytes([0x90]) + struct.pack("<H", h["end"])
        # US references into patched sites
        for p, t, kind, (src, case) in self.us_jump_sites:
            for h in self.hunks:
                if h["X"] < t < h["end"]:
                    assert t >= h["Y"], "US %s @%#x jumps into the replaced range" % (kind, p)
                    struct.pack_into("<H", self.code, p, h["replay"] + t - h["Y"]); self.log.append("moved US %s @%#x into replay" % (kind, p))
                elif t == h["X"] and kind != "code":
                    twin = self.rev.get(src); tgt = None           # the DC instruction paired with the one holding this operand
                    if twin is not None and self.d.code[twin] == u.code[src]:
                        if case is None: tgt = u16(self.d.code, twin + 1)
                        else:
                            ents = switch_table(self.d.code, u16(self.d.code, twin + 1))[0]
                            tgt = ents[case][1] if case < len(ents) else None
                    if tgt == h["lo"]: continue                     # DC jumps into the block too
                    struct.pack_into("<H", self.code, p, h["replay"])
                    self.log.append("US %s @%#x -> %#x skips the DC block (DC twin %s)" % (kind, p, h["replay"], hex(tgt) if tgt else "none"))
        self.new_events = [(k, i, self.func(f)) for k, i, f in self.events]
        self.repointed = [(k, i, self.func(f)) for k, i, f in self.replaced]
        for h in self.hunks:                                        # finally the detour jumps themselves
            self.code[h["X"]:h["X"] + 3] = bytes([0x90]) + struct.pack("<H", h["at"])
            self.log.append("hunk DC %#x-%#x -> detour %#x at US %#x (replay US %#x-%#x, %d bytes)" % (h["lo"], h["hi"], h["at"], h["X"], h["Y"], h["end"], h["end"] - h["Y"]))
        return self._image()

    def _image(self):
        u = self.u; code = bytearray(self.code); data = bytearray(self.data)
        code += bytes(-len(code) % 16); data += bytes(-len(data) % 16)
        assert len(code) < 0x10000 and len(data) < 0x10000
        head = bytearray(u.raw[:u.code0])
        for kind, eid, at in self.repointed:                        # existing US event entries -> copied DC functions
            p = u.nsec * 16; done = False
            while p < u.code0 and not done:
                magic, tbl, units, k, cnt = struct.unpack_from("<IHHHH", head, p)
                if magic == 0x544e5645 and k == kind:
                    for e in range(cnt):
                        q = p + tbl + 8 * e
                        if struct.unpack_from("<I", head, q)[0] == eid: struct.pack_into("<H", head, q + 6, at); done = True
                if units == 0: break
                p += units * 16
            assert done; self.log.append("event (%d, %d) now runs the DC function at %#x" % (kind, eid, at))
        for kind, eid, at in self.new_events:                       # append to the EVNT section of that kind (needs spare room)
            p = u.nsec * 16; done = False
            while p < u.code0:
                magic, tbl, units, k, cnt = struct.unpack_from("<IHHHH", head, p)
                if magic == 0x544e5645 and k == kind:
                    e = p + tbl + cnt * 8; assert tbl + (cnt + 1) * 8 <= units * 16, "no room in the EVNT table"
                    struct.pack_into("<IHH", head, e, eid, 0, at); struct.pack_into("<H", head, p + 10, cnt + 1); done = True
                    self.log.append("event (%d, %d) -> %#x" % (kind, eid, at)); break
                if units == 0: break
                p += units * 16
            assert done
        raw = head + code + data
        struct.pack_into("<H", raw, 8, len(code) // 16); struct.pack_into("<H", raw, 0xa, len(data) // 16)
        if u.reloc_unit:
            struct.pack_into("<H", raw, 0x18, len(raw) // 16); raw += u.raw[u.reloc_unit * 16:]
        out = msc.Msc(bytes(raw))
        lost = [ip for ip in self.u.insns if ip not in out.insns and not any(h["X"] < ip < h["end"] for h in self.hunks)]
        if self.replaced:                                           # the replaced US event functions (and what only they called) go dead
            self.log.append("%d US instructions now unreachable (replaced event code)" % len(lost))
        else:
            assert not lost, "US instruction %#x lost" % lost[0]
        return bytes(raw)
