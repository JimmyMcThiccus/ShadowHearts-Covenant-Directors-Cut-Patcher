"""PCMS helpers for LSD cutscenes: extract the stream, decode it with pcmscodec, align two versions.
usage: lsdaudio.py align DISC PATH   (DISC 1/2: decode the US and DC audio of PATH and print the DC->US offset over time)"""
import sys, os, struct, subprocess, numpy as np, isoset, lsdtracks
CODEC = os.path.join(os.path.dirname(__file__), "..", "pcmscodec", "target", "release", "pcmscodec.exe")
TMP = os.path.join(os.path.dirname(__file__), "..", "x", "aud"); os.makedirs(TMP, exist_ok=True)

def pcms(b):
    """(track index, header offset, stream bytes) of an LSD's PCMS track."""
    n, tps, dur, tr = lsdtracks.tracks(b)
    k = [i for i in range(n) if tr[i][1] == "PCMS"][0]
    ho = 0x40 + sum(t[5] for t in tr[:k])
    p = 0x40 + sum(t[5] for t in tr); out = bytearray()
    while p < len(b):
        t, _, seq, nb = struct.unpack_from("<HHII", b, p)
        if t == k: out += b[p + 16:p + 16 + nb * 16]
        p += 16 + nb * 16
    return k, ho, bytes(out)

def decode(stream, name):
    a, r = os.path.join(TMP, name + ".pcms"), os.path.join(TMP, name + ".raw")
    open(a, "wb").write(stream); subprocess.run([CODEC, "decode", a, r], check=True, capture_output=True)
    return np.frombuffer(open(r, "rb").read(), "<i2").reshape(-1, 2).astype(np.float32)

def envelope(x, hop=480):
    m = x.mean(1); n = len(m) // hop
    e = np.sqrt((m[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-3)
    d = np.maximum(np.diff(np.log(e), prepend=np.log(e[0])), 0)     # onset strength, 100 Hz
    return d

def offsets(us, dc, win=400, step=100, search=600):
    """For windows of the US onset curve (4 s, every 1 s), the best DC lag (in 10 ms units) within +-6 s, and its score."""
    eu, ed = envelope(us), envelope(dc); res = []
    for s in range(0, max(1, len(eu) - win), step):
        a = eu[s:s + win]; a = (a - a.mean()) / (a.std() + 1e-9); best = (-9, 0)
        for lag in range(-search, search + 1, 2):
            o = s + lag
            if o < 0 or o + win > len(ed): continue
            b = ed[o:o + win]; c = float(np.dot(a, (b - b.mean()) / (b.std() + 1e-9)) / win)
            if c > best[0]: best = (c, lag)
        res.append((s / 100, best[1] / 100, round(best[0], 2)))
    return res

if __name__ == "__main__" and sys.argv[1] == "align":
    d, p = sys.argv[2], sys.argv[3]
    us = decode(pcms(isoset.Disc("us" + d).read(p))[2], "us"); dc = decode(pcms(isoset.Disc("dc" + d).read(p))[2], "dc")
    print("US %.2fs DC %.2fs" % (len(us) / 48000, len(dc) / 48000))
    for t, off, sc in offsets(us, dc): print("%6.1f  %+6.2f  %.2f" % (t, off, sc))

def sbtd(b):
    """(payload bytes, packet room, [(start, end)...]) of an LSD's subtitle pack, or None."""
    n, tps, dur, tr = lsdtracks.tracks(b)
    ks = [i for i in range(n) if tr[i][1] == "SBTD"]
    if not ks: return None
    k = ks[0]; p = 0x40 + sum(t[5] for t in tr)
    while p < len(b):
        t, _, seq, nb = struct.unpack_from("<HHII", b, p)
        if t == k:
            s = b[p + 16:p + 16 + nb * 16]; nl = struct.unpack_from("<h", s, 0)[0]; lt = struct.unpack_from("<I", s, 0x14)[0]
            return s, nb * 16, [struct.unpack_from("<ff", s, lt + i * 0x20 + 0x14) for i in range(nl)]
        p += 16 + nb * 16
