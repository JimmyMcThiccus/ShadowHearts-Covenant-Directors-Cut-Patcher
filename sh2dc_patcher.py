#!/usr/bin/env python3
"""Shadow Hearts: Covenant - Director's Cut content port, patcher.

Builds a patched copy of your US *Shadow Hearts: Covenant* discs, using your own copies of the US discs and the Japanese
*Shadow Hearts II Director's Cut* discs.  The patch data holds no game files: it is a list of instructions ("copy these bytes from
your disc") plus the new material (English translation, code patches, dub audio, title plate).

    python sh2dc_patcher.py --edition regular --us1 US1.iso --us2 US2.iso --dc1 DC1.iso --dc2 DC2.iso --out OUTDIR
    python sh2dc_patcher.py --edition undub   ... (same inputs)

  --edition regular  English, with the Director's Cut content added.
  --edition undub    The same, with Japanese voices in every cutscene (English subtitles kept).
  --discs 1          Build only disc 1 (default: both).  Disc N needs --usN and --dcN.

Your ISOs are never modified; each output is a new file.  Needs Python 3.8+.  The UnDub edition also needs numpy and the
bundled `pcmscodec` program for two cutscenes whose Japanese audio is resampled (without them those two keep English audio).
"""
import argparse, hashlib, json, os, shutil, struct, subprocess, sys, tempfile, threading, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.join(HERE, "patchdata.zip")

# ---------------------------------------------------------------------------------------------------------------- disc image
class Iso:
    """Minimal ISO9660 root-directory reader (the game keeps every file it uses in the root directory)."""
    def __init__(self, path, mode="rb"):
        self.path = path; self.f = open(path, mode)
        self.f.seek(16 * 2048); pvd = self.f.read(2048)
        if pvd[1:6] != b"CD001": raise SystemExit("%s is not an ISO image" % path)
        root = pvd[156:190]; lba, size = struct.unpack_from("<I", root, 2)[0], struct.unpack_from("<I", root, 10)[0]
        self.root_lba, self.root_size, self.files = lba, size, {}
        self.f.seek(lba * 2048); d = self.f.read(size); i = 0
        while i < len(d):
            n = d[i]
            if n == 0: i = (i // 2048 + 1) * 2048; continue
            flba, fsz = struct.unpack_from("<I", d, i + 2)[0], struct.unpack_from("<I", d, i + 10)[0]
            self.files[d[i + 33:i + 33 + d[i + 32]].decode("ascii", "replace").split(";")[0]] = (flba, fsz); i += n
    def read_at(self, lba, size):
        self.f.seek(lba * 2048); return self.f.read(size)
    def close(self): self.f.close()

# ---------------------------------------------------------------------------------------------------------------- PKFINFO.TBL
AL = ".0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
def encode_name(name):
    d = [AL.index(c) + 1 for c in name.upper() if c in AL][:12]; d += [0] * (12 - len(d)); hi, lo = [], []
    for g in range(3):
        u = d[g * 4] + d[g * 4 + 1] * 40 + d[g * 4 + 2] * 1600 + d[g * 4 + 3] * 64000; hi.append(u >> 16); lo.append(u & 0xffff)
    return struct.pack(">4H", hi[0] + hi[1] * 40 + hi[2] * 1600, lo[0], lo[1], lo[2])

class Table:
    """The game's file table: 16-byte entries {name key[8], u32 offset (16-byte units from the parent), u32 size | dir flag}."""
    def __init__(self, iso):
        self.iso = iso; raw = iso.read_at(*iso.files["PKFINFO.TBL"]); self.raw = bytearray(raw)
        n = struct.unpack_from("<H", raw, 0)[0]
        self.ent = [[raw[16 + i * 16:24 + i * 16]] + list(struct.unpack_from("<II", raw, 24 + i * 16)) for i in range(n)]
        self.dircount = next((e[2] & 0x7fffffff) // 16 for e in self.ent if e[2] & 0x80000000) - 1
    def search(self, start, key):                       # FileIOLib::searchInfo: linear scan to the end of the table
        for i in range(start, len(self.ent)):
            if start == 0 and self.dircount < i: break
            if self.ent[i][0] == key: return i
        return -1
    def find(self, path):
        """(entry index or -1, lba, size, child list start) of a path, the way the game resolves it."""
        lst, lba, i = 0, 0, -1
        for comp in path.split("/"):
            i = self.search(lst, encode_name(comp))
            if i < 0: return None
            key, off, sz = self.ent[i]
            lba = self.iso.files[comp + ("" if "." in comp else ".PKB")][0] if lst == 0 else lba + (off >> 7)
            if sz & 0x80000000: lst += (sz & 0x7fffffff) // 16
        return i, lba, (None if self.ent[i][2] & 0x80000000 else self.ent[i][2]), lst
    def read(self, path):
        r = self.find(path)
        if r is None or r[2] is None: return None
        return self.iso.read_at(r[1], r[2])
    def pack(self):
        n = len(self.ent)
        return (struct.pack("<HHI", n, 16, n * 16) + bytes(self.raw[8:16]) +
                b"".join(k + struct.pack("<II", o, s) for k, o, s in self.ent))

def fmt_size(n):
    """decimal GB (what disc and DVD capacities use) and GiB (what Windows Explorer shows, labelled "GB")"""
    return "%.2f GB (%.2f GiB)" % (n / 1e9, n / 2**30)

def read_file(iso, table, name):
    """A file by disc path: root files ("FIELD.BIN") or packed ones ("FIELD/MPS/KS_00_U.MSC")."""
    if "/" not in name: return iso.read_at(*iso.files[name])
    return table.read(name)

# ---------------------------------------------------------------------------------------------------------------- deltas
def apply_delta(delta, sources):
    """Rebuild a file: ops 'C' src u8, off u32, len u32 (copy from a source) and 'A' len u32 + bytes (new data)."""
    out = bytearray(); p = 0
    while p < len(delta):
        op = delta[p]
        if op == 0x43:
            s, off, n = struct.unpack_from("<BII", delta, p + 1); out += sources[s][off:off + n]; p += 10
        elif op == 0x41:
            n = struct.unpack_from("<I", delta, p + 1)[0]; out += delta[p + 5:p + 5 + n]; p += 5 + n
        else: raise ValueError("bad delta")
    return bytes(out)

md5 = lambda b: hashlib.md5(b).hexdigest()

# ---------------------------------------------------------------------------------------------------------------- UnDub resampling
def resample_scene(us_lsd, dc_lsd, rec, codec, tmp):
    """The two Director's Cut cutscenes with 44.1 kHz audio: decode the Japanese track, resample to 48 kHz, encode it into the US
    file's audio packets, then set the stored header field and subtitle times."""
    import numpy as np
    def pcms_track(b):
        n = struct.unpack_from("<H", b, 0xa)[0]; p = 0x40; hs = []
        for i in range(n):
            hs.append((b[p:p + 4], p)); p += struct.unpack_from("<H", b, p + 0x10)[0] * 16
        k = [i for i, (t, _) in enumerate(hs) if t == b"PCMS"][0]; return k, hs[k][1], p
    def packets(b, k, first):
        p = first
        while p < len(b):
            t, _, seq, nb = struct.unpack_from("<HHII", b, p)
            if t == k: yield p + 16, nb * 16
            p += 16 + nb * 16
    kd, hd, fd = pcms_track(dc_lsd); stream = b"".join(dc_lsd[a:a + n] for a, n in packets(dc_lsd, kd, fd))
    rate = struct.unpack_from("<H", dc_lsd, hd + 0x26)[0]
    a, r = os.path.join(tmp, "jp.pcms"), os.path.join(tmp, "jp.raw")
    open(a, "wb").write(stream); subprocess.run([codec, "decode", a, r], check=True, capture_output=True)
    x = np.frombuffer(open(r, "rb").read(), "<i2").reshape(-1, 2).astype(np.float64)
    n_out = int(round(len(x) * 48000 / rate))
    try:
        from scipy.signal import resample_poly; y = resample_poly(x, 48000 // 300, rate // 300, axis=0)
    except ImportError:                       # numpy-only fallback: band-limited FFT resample of the whole track
        X = np.fft.rfft(x, axis=0); Y = np.zeros((n_out // 2 + 1, 2), complex); m = min(len(X), len(Y)); Y[:m] = X[:m]
        y = np.fft.irfft(Y, n_out, axis=0) * (n_out / len(x))
    out = bytearray(us_lsd); ku, hu, fu = pcms_track(out); room = sum(n for _, n in packets(out, ku, fu))
    cap = room // 2 // 16 * 28; y = np.clip(np.round(y[:cap]), -32768, 32767).astype("<i2")
    raw, enc = os.path.join(tmp, "jp48.raw"), os.path.join(tmp, "jp48.pcms")
    open(raw, "wb").write(y.tobytes()); subprocess.run([codec, "encode", raw, enc, str(room)], check=True, capture_output=True)
    st = open(enc, "rb").read(); q = 0
    for a, n in list(packets(out, ku, fu)): out[a:a + n] = st[q:q + n]; q += n
    struct.pack_into("<I", out, hu + 0x28, min((len(y) + 27) // 28 * 16, room // 2))
    nt = struct.unpack_from("<H", out, 0xa)[0]; p = 0x40; ks = None
    for i in range(nt):
        if out[p:p + 4] == b"SBTD": ks = i
        p += struct.unpack_from("<H", out, p + 0x10)[0] * 16
    if ks is not None and rec.get("times"):
        for a, n in packets(out, ks, fu):
            lt = struct.unpack_from("<I", out, a + 0x14)[0]
            for i, (s, e) in enumerate(rec["times"]): struct.pack_into("<ff", out, a + lt + i * 0x20 + 0x14, s, e)
            break
    return bytes(out)

# ---------------------------------------------------------------------------------------------------------------- build
def build_disc(d, edition, us_path, dc_path, out_path, man, z, codec):
    D = man["discs"][d]; E = D[edition]
    print("\n== Disc %s (%s) ==" % (d, edition))
    us, dc = Iso(us_path), Iso(dc_path); ut, dt = Table(us), Table(dc)
    for tag, iso, tbl in (("us", us, ut), ("dc", dc, dt)):
        if md5(iso.read_at(*iso.files["PKFINFO.TBL"])) != D["tables"][tag]:
            raise SystemExit("%s does not look like the expected %s disc %s (file table differs). Check the dump and the disc number."
                             % (iso.path, "US" if tag == "us" else "Director's Cut", d))
    src_cache = {}                                   # small files only: cutscenes run to 90 MB and are each used once
    local, zlock = threading.local(), threading.Lock()
    def source(ref):
        if ref in src_cache: return src_cache[ref]
        if not hasattr(local, "us"):                 # every worker thread reads through its own file handles
            local.us = Iso(us_path); local.dc = Iso(dc_path); local.ut = Table(local.us); local.dt = Table(local.dc)
        tag, name = ref.split(":", 1)
        b = read_file(local.us, local.ut, name) if tag == "us" else read_file(local.dc, local.dt, name)
        if b is None or md5(b) != man["sources"][d][ref]:
            raise ValueError("%s on your %s disc %s differs from the expected file (bad dump or different release)." % (name, tag.upper(), d))
        if len(b) < (4 << 20): src_cache[ref] = b
        return b
    def make(spec):
        if "copy" in spec: data = source(spec["copy"])
        else:
            with zlock: delta = z.read(spec["delta"])
            data = apply_delta(delta, [source(s) for s in spec["src"]])
        if md5(data) != spec["md5"]: raise ValueError("internal error: rebuilt file does not match (%s)" % spec.get("delta"))
        return data
    def made(pairs):
        """(path, data) in order, rebuilt on every CPU thread with a bounded number of files in flight."""
        from concurrent.futures import ThreadPoolExecutor
        pairs = list(pairs); n = os.cpu_count() or 1
        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = []
            for k, (path, spec) in enumerate(pairs):
                futs.append((path, ex.submit(make, spec)))
                while len(futs) > 2 * n or (k == len(pairs) - 1 and futs):
                    p, fu = futs.pop(0)
                    try: yield p, fu.result()
                    except ValueError as e: raise SystemExit(str(e))

    print("copying %s -> %s" % (os.path.basename(us_path), out_path))
    shutil.copyfile(us_path, out_path)
    o = Iso(out_path, "r+b"); T = Table(o); f = o.f
    f.seek(0, 2); end = f.tell() // 2048
    def write(at, data):
        f.seek(at * 2048); f.write(data + bytes(-len(data) % 2048))
    secs = lambda n: (n + 2047) // 2048
    # Placement plan, so the result stays as small as possible (single-layer DVD): a replaced file is written over the old one when
    # it fits; otherwise the old space is freed, and new or moved files fill the freed gaps (largest file first, best fit) before
    # anything is appended.  A file's offset counts from its directory's base sector, so a gap must lie after that base.
    jobs = list(E["replace"]); place, holes, need = {}, [], []
    for path, spec in jobs:
        i, lba, size, _ = T.find(path)
        if secs(spec["size"]) <= secs(size): place[path] = ("inplace", lba)
        else: holes.append([lba, secs(size)]); need.append((spec["size"], path, lba - (T.ent[i][1] >> 7)))
    for path, spec in E["new"]: need.append((spec["size"], path, T.find(path.rsplit("/", 1)[0])[1]))
    for size, path, base in sorted(need, reverse=True):
        fit = [h for h in holes if h[1] >= secs(size) and h[0] >= base]
        if fit:
            h = min(fit, key=lambda h: h[1]); place[path] = ("hole", h[0]); h[0] += secs(size); h[1] -= secs(size)
        else:
            place[path] = ("append", end); end += secs(size)
    # 1. files only the Director's Cut has: new table entries at the end of the table
    added = []
    for path, data in made(E["new"]):
        d_, name = path.rsplit("/", 1); base = T.find(d_)
        at = place[path][1]; write(at, data); added.append([encode_name(name), (at - base[1]) << 7, len(data)])
    print("added %d Director's Cut files" % len(added))
    # 2. replaced files
    count = {"inplace": 0, "hole": 0, "append": 0}
    for path, data in made(jobs):
        i, lba, size, _ = T.find(path); how, at = place[path]; write(at, data); count[how] += 1
        if how == "inplace": T.ent[i][2] = len(data)
        else: base = lba - (T.ent[i][1] >> 7); T.ent[i][1:] = [(at - base) << 7, len(data)]
    print("replaced %d files (%d in place, %d moved into freed space, %d appended)" % (len(jobs), count["inplace"], count["hole"], count["append"]))
    def append(data):
        nonlocal end
        at = end; write(at, data); end += secs(len(data)); return at
    # 3. UnDub scenes rebuilt by resampling (needs numpy + pcmscodec)
    for path, rec in E.get("resample", []):
        try:
            ui, di = Iso(us_path), Iso(dc_path); ub, db = read_file(ui, Table(ui), path), read_file(di, Table(di), path); ui.close(); di.close()
            if md5(ub) != rec["us_md5"] or md5(db) != rec["dc_md5"]: raise ValueError("source file differs from the expected one")
            with tempfile.TemporaryDirectory() as tmp:
                data = resample_scene(ub, db, rec, codec, tmp)
            i, lba, size, _ = T.find(path); assert len(data) == size
            f.seek(lba * 2048); f.write(data); print("resampled Japanese audio into", path)
        except Exception as e:
            print("WARNING: %s keeps its English audio (resampling needs numpy and pcmscodec: %s)" % (path, e))
    # 4. the file table: rewritten at the end, root directory record repointed
    T.ent += added; end = write_table(o, T, end)
    # 5. root files patched in place (same size)
    for name, spec in E["root"]:
        data = make(spec); lba, size = o.files[name]; assert len(data) == size; f.seek(lba * 2048); f.write(data)
    f.close()
    # 6. check every patched file through a fresh read of the output
    v = Iso(out_path); V = Table(v); bad = 0
    for path, spec in E["new"] + E["replace"] + E["root"]:
        b = read_file(v, V, path)
        if b is None or md5(b) != spec["md5"]: bad += 1; print("  check failed:", path)
    v.close(); dc.close(); us.close()
    size = os.path.getsize(out_path); dvd5 = 2295104 * 2048
    print("disc %s done: %s (%s)" % (d, out_path, "all files verified" if not bad else "%d FAILED" % bad))
    print("size %s: %s" % (fmt_size(size), ("fits a single-layer DVD (limit %s, %.0f MB to spare)" % (fmt_size(dvd5), (dvd5 - size) / 1e6)) if size <= dvd5
          else "too big for a single-layer DVD by %.1f MB (use a dual-layer disc)" % ((size - dvd5) / 1e6)))
    return bad

def write_table(o, T, end):
    """Write the file table past `end`, repoint the root directory record and the volume size.  Returns the new end sector."""
    f = o.f; tbl = T.pack(); tbl_lba = end; f.seek(end * 2048); f.write(tbl + bytes(-len(tbl) % 2048)); end += (len(tbl) + 2047) // 2048
    f.seek(o.root_lba * 2048); dr = bytearray(f.read(o.root_size)); i = 0
    while i < len(dr):
        L = dr[i]
        if L == 0: i = (i // 2048 + 1) * 2048; continue
        if dr[i + 33:i + 33 + dr[i + 32]].split(b";")[0] == b"PKFINFO.TBL":
            struct.pack_into("<I", dr, i + 2, tbl_lba); struct.pack_into(">I", dr, i + 6, tbl_lba)
            struct.pack_into("<I", dr, i + 10, len(tbl)); struct.pack_into(">I", dr, i + 14, len(tbl))
        i += L
    f.seek(o.root_lba * 2048); f.write(dr)
    f.seek(16 * 2048); pvd = bytearray(f.read(2048))
    struct.pack_into("<I", pvd, 80, end); struct.pack_into(">I", pvd, 84, end); f.seek(16 * 2048); f.write(pvd)
    return end

# ---------------------------------------------------------------------------------------------------------------- single disc
# The two US discs run the same program and hold the same files except their cutscenes (LSD/, 90 on disc 1, 75 on disc 2).  The game
# learns which disc is in from the volume set id ("0"/"1") read at boot; a disc change (DiskChange: story, loading a save, Theater
# disc switch) stores the wanted number and re-reads the volume header, and InitPkb reports "wrong disc" when the numbers differ.
# SLUS_210.41 patches (address, original word, new word):
#   0x2289d4 InitPkb: beq v1,v0,+6 (volume disc number == wanted) -> b +6, so every disc change succeeds at once;
#   0x407604 loading a save made on "the other disc": bne v0,v1 (ask for that disc) -> sw v1,-0x7d80(gp) (adopt its number).
#   0x22ab0c disc thread, state 3 "wait for the tray to open and close": beq v0,1 -> b, so it goes straight on to check the disc
#            (with one disc there is never a tray event, and the change would wait forever).
def _beq(rs, rt, off): return (4 << 26) | (rs << 21) | (rt << 16) | (off & 0xffff)
EXE_PATCHES = [(0x2289d4, _beq(3, 2, (0x2289f0 - 0x2289d8) >> 2), _beq(0, 0, (0x2289f0 - 0x2289d8) >> 2)),
               (0x407604, (5 << 26) | (2 << 21) | (3 << 16) | (((0x407628 - 0x407608) >> 2) & 0xffff), (0x2b << 26) | (28 << 21) | (3 << 16) | (-0x7d80 & 0xffff)),
               (0x22ab0c, _beq(2, 3, (0x22ab20 - 0x22ab10) >> 2), _beq(0, 0, (0x22ab20 - 0x22ab10) >> 2))]
# DC_01_U (the disc-change scene): "push 2; callu 0x25c7 n=1" (show DSKCHG2 "insert disc 2", DiskChange(2)) -> "push 2; push 0;
# DiskChange n=2" (change straight away); the save prompt before it stays.
DC01_IP, DC01_OLD, DC01_NEW = 0x25b9, bytes.fromhex("081bc72501"), bytes.fromhex("0806c26f02")

def make_single(d1_path, d2_path, out_path, us2_path):
    """Disc 1 build + disc 2's cutscenes in one image, with the disc checks patched out."""
    print("\n== Single disc ==")
    os.replace(d1_path, out_path)
    o = Iso(out_path, "r+b"); T = Table(o); f = o.f; f.seek(0, 2); end = f.tell() // 2048
    d2 = Iso(d2_path); T2 = Table(d2); u2 = Iso(us2_path); U2 = Table(u2)
    # disc 2's own cutscene list, from its original table (the patched one also has the appended Director's Cut entries at the end)
    i = U2.search(0, encode_name("LSD")); start = U2.ent[i][2] & 0x7fffffff; start //= 16
    starts = sorted({(e[2] & 0x7fffffff) // 16 for e in U2.ent if e[2] & 0x80000000})
    stop = next((s for s in starts if s > start), len(U2.ent))
    names = [U2.ent[k][0] for k in range(start, stop)]
    lsd_base = T.find("LSD")[1]; added = []
    for key in names:
        data = read_file(d2, T2, "LSD/" + decode_key(key)); size = len(data)
        at = end; f.seek(at * 2048); f.write(data + bytes(-size % 2048)); end += (size + 2047) // 2048
        added.append([key, (at - lsd_base) << 7, size])
    T.ent += added; end = write_table(o, T, end)
    print("added disc 2's %d cutscenes" % len(added))
    # program patches
    lba, size = o.files["SLUS_210.41"]; f.seek(lba * 2048); elf = bytearray(f.read(size))
    ph, n = struct.unpack_from("<I", elf, 0x1c)[0], struct.unpack_from("<H", elf, 0x2c)[0]
    segs = [struct.unpack_from("<8I", elf, ph + 32 * k) for k in range(n)]
    for addr, old, new in EXE_PATCHES:
        s = next(s for s in segs if s[2] <= addr < s[2] + s[4]); fo = s[1] + addr - s[2]
        if struct.unpack_from("<I", elf, fo)[0] != old: raise SystemExit("unexpected game program (SLUS_210.41) at %#x" % addr)
        struct.pack_into("<I", elf, fo, new)
    f.seek(lba * 2048); f.write(elf)
    i, lba, size, _ = T.find("FIELD/MPS/DC_01_U.MSC"); f.seek(lba * 2048); msc = bytearray(f.read(size))
    code0 = msc[1] * 16 + struct.unpack_from("<H", msc, 6)[0] * 16
    if msc[code0 + DC01_IP:code0 + DC01_IP + 5] != DC01_OLD: raise SystemExit("unexpected DC_01_U.MSC")
    msc[code0 + DC01_IP:code0 + DC01_IP + 5] = DC01_NEW; f.seek(lba * 2048); f.write(msc); f.close()
    # check
    v = Iso(out_path); V = Table(v); bad = 0
    for key in names:
        name = decode_key(key); a, b = read_file(v, V, "LSD/" + name), read_file(d2, T2, "LSD/" + name)
        if a is None or a != b: bad += 1; print("  check failed: LSD/" + name)
    v.close(); d2.close(); u2.close(); os.remove(d2_path)
    size = os.path.getsize(out_path); dvd9 = 4171712 * 2048
    print("single disc done: %s (%s)" % (out_path, "all files verified" if not bad else "%d FAILED" % bad))
    print("size %s: %s" % (fmt_size(size), ("fits a dual-layer DVD (limit %s)" % fmt_size(dvd9)) if size <= dvd9 else "too big for a dual-layer DVD"))
    return bad

def decode_key(k):
    s = ""; w0, l0, l1, l2 = struct.unpack(">4H", k)
    for hi, lo in zip((w0 % 40, (w0 // 40) % 40, w0 // 1600), (l0, l1, l2)):
        u = (hi << 16) | lo
        for _ in range(4):
            c = u % 40; u //= 40
            if c: s += AL[c - 1]
    return s

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edition", choices=("regular", "undub"), required=True)
    for k in ("us1", "us2", "dc1", "dc2"): ap.add_argument("--" + k, help="path to the %s disc %s ISO" % ("US" if k[:2] == "us" else "Director's Cut", k[2]))
    ap.add_argument("--discs", default="1,2"); ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--single-disc", action="store_true", help="one dual-layer image with both discs' content and no disc swaps")
    a = ap.parse_args()
    if not os.path.exists(PATCH): raise SystemExit("patchdata.zip must sit next to this script")
    z = zipfile.ZipFile(PATCH); man = json.loads(z.read("manifest.json"))
    codec = next((os.path.join(HERE, n) for n in ("pcmscodec.exe", "pcmscodec") if os.path.exists(os.path.join(HERE, n))), "pcmscodec")
    os.makedirs(a.out, exist_ok=True); bad = 0
    tag = " UnDub" if a.edition == "undub" else ""
    if a.single_disc:
        for k in ("us1", "us2", "dc1", "dc2"):
            if not getattr(a, k): raise SystemExit("--single-disc needs all four ISOs (--us1 --us2 --dc1 --dc2)")
        t1, t2 = os.path.join(a.out, "~disc1.tmp.iso"), os.path.join(a.out, "~disc2.tmp.iso")
        bad += build_disc("2", a.edition, a.us2, a.dc2, t2, man, z, codec)
        bad += build_disc("1", a.edition, a.us1, a.dc1, t1, man, z, codec)
        out = os.path.join(a.out, "Shadow Hearts - Covenant (USA) [DC v%s%s Single Disc].iso" % (man["version"], tag))
        bad += make_single(t1, t2, out, a.us2)
        print("\nFinished." if not bad else "\nFinished with errors."); sys.exit(1 if bad else 0)
    for d in a.discs.split(","):
        d = d.strip(); us, dc = getattr(a, "us" + d), getattr(a, "dc" + d)
        if not us or not dc: raise SystemExit("disc %s needs --us%s and --dc%s" % (d, d, d))
        out = os.path.join(a.out, "Shadow Hearts - Covenant (USA) (Disc %s) [DC v%s%s].iso" % (d, man["version"], " UnDub" if a.edition == "undub" else ""))
        bad += build_disc(d, a.edition, us, dc, out, man, z, codec)
    print("\nFinished." if not bad else "\nFinished with errors.")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
