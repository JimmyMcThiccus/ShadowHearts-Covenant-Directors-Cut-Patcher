"""MSC field-script image: parse, walk code (port of sh2_script::disasm::scan_calls), find data references, rebuild.
Layout (notes/E/script_vm.md 1.2): hdr 0x20, EVNT dir (dirUnits*16), code (codeUnits*16), data (dataUnits*16), reloc @ relocUnit*16."""
import struct

def u16(b, o): return struct.unpack_from("<H", b, o)[0]

class Msc:
    def __init__(self, raw):
        self.raw = bytes(raw)
        self.nsec = raw[1]; self.dir_units, self.code_units, self.data_units = struct.unpack_from("<HHH", raw, 6)
        self.bss, self.start, self.end = struct.unpack_from("<HHH", raw, 0xc)
        self.reloc_unit = u16(raw, 0x18)
        self.code0 = self.nsec*16 + self.dir_units*16; self.data0 = self.code0 + self.code_units*16
        self.code = bytearray(raw[self.code0:self.data0]); self.data = bytearray(raw[self.data0:self.data0 + self.data_units*16])
        self.events = []
        p = self.nsec*16
        while p < self.code0:
            magic, tbl, units, kind, cnt = struct.unpack_from("<IHHHH", raw, p)
            if magic == 0x544e5645:
                self.events += [(kind, struct.unpack_from("<I", raw, p+tbl+i*8)[0], u16(raw, p+tbl+i*8+6)) for i in range(cnt)]
            if units == 0: break
            p += units*16
        self.relocs = []
        if self.reloc_unit:
            r = self.reloc_unit*16; n = u16(raw, r)
            self.reloc_hdr = raw[r:r+4]
            self.relocs = [struct.unpack_from("<HH", raw, r+4+i*4) for i in range(n)]
        self.walk()

    def walk(self):
        """Visit all reachable instructions.  self.insns: ip -> (op, length); self.dref: list of (operand_ip, data_off)."""
        code = self.code; funcs = {self.start}
        if self.end != 0xffff: funcs.add(self.end)
        funcs |= {e[2] for e in self.events}
        done = set(); self.insns = {}; self.dref = []; seen = set()
        while funcs - done:
            f = min(funcs - done); done.add(f)
            work = [f + 2]; visited = set()
            while work:
                ip = work.pop(); stack = []; last = None
                while ip not in visited and ip < len(code):
                    visited.add(ip); b = code[ip]; at = ip; ip += 1
                    def push(v):
                        nonlocal last; last = v; stack.append(v)
                    if b >= 0xa0:
                        if b > 0xbb: ip += 1
                        n = code[ip] if ip < len(code) else 0; ip += 1
                        del stack[len(stack)-min(n, len(stack)):]; stack.append(None)
                    elif b >= 0x90:
                        stack.clear()
                        if b == 0x90:
                            work.append(u16(code, ip)); ip += 2; self.insns[at] = (b, ip-at); break
                        elif b in (0x91, 0x92): work.append(u16(code, ip)); ip += 2
                        elif b == 0x94:
                            tbl = u16(code, ip); p = tbl; h = u16(code, p); p += 2; kt = (h >> 12) & 7
                            for _ in range(h & 0xfff):
                                p += {2: 4, 1: 2}.get(kt, 1); work.append(u16(code, p)); p += 2
                            if h & 0x8000: work.append(u16(code, p)); self.insns[at] = (b, 3); break
                            ip += 2; self.insns[at] = (b, ip-at); ip = p; continue
                        elif b in (0x98, 0x99): self.insns[at] = (b, 1); break
                    elif b >= 0x20:
                        if b in (0x8e, 0x8f): del stack[-3:]; stack.append(None)
                        elif b == 0x8d: ip += 2; stack[-1:] = []
                        elif b == 0x8c:
                            n = (stack.pop() if stack else None)
                            n = n if n is not None else (last or 0); ip += min(n, 0x1000)
                        elif b == 0x8b: ip += 1; stack[-1:] = []
                        elif b == 0x8a: stack[-1:] = []
                        elif 0x80 <= b <= 0x89 or 0x60 <= b <= 0x63:
                            s = code[ip]; ip += 1
                            if s & 0xc0 == 0xc0: ip += 1
                            if b >= 0x80: del stack[-2:]
                            else: stack[-1:] = []
                            stack.append(None)
                        elif 0x70 <= b <= 0x7a or 0x67 <= b <= 0x6d: del stack[-2:]; stack.append(None)
                        else: stack[-1:] = []; stack.append(None)
                    else:
                        if b == 0x00: self.insns[at] = (b, 1); break
                        elif b == 0x01: stack.clear()
                        elif b in (0x04, 0x05, 0x06, 0x07, 0x08, 0x09): push(None)
                        elif b in (0x0a, 0x0b): push(code[ip]); ip += 1
                        elif b in (0x0c, 0x0d): push(u16(code, ip)); ip += 2
                        elif b in (0x0e, 0x0f): push(struct.unpack_from("<I", code, ip)[0]); ip += 4
                        elif 0x10 <= b <= 0x13 or b == 0x19: ip += 1; stack.append(None)
                        elif b in (0x14, 0x16, 0x18, 0x1a): ip += 2; stack.append(None)
                        elif b == 0x15:
                            if at not in seen: seen.add(at); self.dref.append((at + 1, u16(code, ip)))
                            ip += 2; stack.append(None)
                        elif b == 0x1b:
                            funcs.add(u16(code, ip)); n = code[ip+2]; ip += 3
                            del stack[len(stack)-min(n, len(stack)):]; stack.append(None)
                    self.insns[at] = (b, ip-at)
        self.dref.sort()

    def cstr(self, off):
        e = self.data.find(b"\0", off); return bytes(self.data[off:e if e >= 0 else len(self.data)])

    def data_reloc_targets(self):
        """(segment, word offset, data offset) of relocated words whose base is the data segment."""
        out = []
        for flags, off in self.relocs:
            seg, base = flags & 0xf, (flags >> 4) & 0xf
            if base != 0:
                tgt = self.code if seg == 0 else self.data
                out.append((seg, off, struct.unpack_from("<I", tgt, off)[0]))
        return out

    def build(self, new_strings):
        """new_strings: {operand_ip: bytes} -> new image with each listed 0x15 operand pointing at an appended NUL-terminated string."""
        code = bytearray(self.code); data = bytearray(self.data)
        cache = {}
        for ip, s in sorted(new_strings.items()):
            if s not in cache:
                cache[s] = len(data); data += s + b"\0"
            assert cache[s] < 0x10000, "data segment would exceed the u16 operand range"
            struct.pack_into("<H", code, ip, cache[s])
        data += b"\0" * (-len(data) % 16)
        raw = bytearray(self.raw[:self.code0]) + code + data
        struct.pack_into("<H", raw, 0xa, len(data)//16)
        if self.reloc_unit:
            reloc = self.raw[self.reloc_unit*16:]
            struct.pack_into("<H", raw, 0x18, len(raw)//16)
            raw += reloc
        return bytes(raw)
