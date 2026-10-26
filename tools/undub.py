"""Build the Japanese-audio ("UnDub") cutscene files for one disc.  usage: undub.py DISC OUT_DIR
For every US cutscene (LSD/*.LSD, OPENING/DEMO.LSD) with audio:
  * swap  - the Japanese track has the same length (within 0.3 s): the DC PCMS stream is copied into the US file (cut or padded
            with silent ADPCM to the US size; only a 44.1 kHz track is resampled and re-encoded), the US English subtitles are kept
            and moved to the Japanese line times;
  * dc    - the US re-timed the scene: the Director's Cut file is used whole, with the US subtitle pack grafted in (when it fits);
  * the opening movie (OPENING/DEMO.LSD) is the Director's Cut one, as is.
Writes OUT_DIR/<disc path> for every changed file and OUT_DIR/undub_disc<N>.json (what was done to each)."""
import sys, os, struct, json, subprocess, numpy as np
from scipy.signal import resample_poly
import isoset, lsdtracks, lsdaudio as L

def pcms_hdr(b):
    n, tps, dur, tr = lsdtracks.tracks(b); k = [i for i in range(n) if tr[i][1] == "PCMS"][0]
    return k, 0x40 + sum(t[5] for t in tr[:k]), tr[k][7]

def put_pcms(b, stream):
    """Write a PCMS stream into b's PCMS packets (same total size)."""
    n, tps, dur, tr = lsdtracks.tracks(b); k = [i for i in range(n) if tr[i][1] == "PCMS"][0]
    p = 0x40 + sum(t[5] for t in tr); q = 0
    while p < len(b):
        t, _, seq, nb = struct.unpack_from("<HHII", b, p)
        if t == k: b[p + 16:p + 16 + nb * 16] = stream[q:q + nb * 16]; q += nb * 16
        p += 16 + nb * 16
    assert q == len(stream), (q, len(stream))

def match_times(us, dc):
    """US subtitle times moved onto the Japanese timeline: 1:1 when the line counts agree, else through a piecewise-linear map
    built from a monotone nearest-start pairing (pairs further apart than 3 s are ignored)."""
    if len(us) == len(dc): return [list(t) for t in dc]
    pairs, j = [], 0
    for a, _ in us:
        while j + 1 < len(dc) and abs(dc[j + 1][0] - a) <= abs(dc[j][0] - a): j += 1
        if abs(dc[j][0] - a) <= 3 and (not pairs or dc[j][0] > pairs[-1][1]): pairs.append((a, dc[j][0]))
    if len(pairs) < 2: return [list(t) for t in us]
    xs, ys = zip(*pairs)
    f = lambda t: float(np.interp(t, xs, ys, left=t - xs[0] + ys[0], right=t - xs[-1] + ys[-1]))
    return [[f(a), f(a) + (e - a)] for a, e in us]

def set_times(b, times):
    """Patch the line times of b's subtitle pack in place."""
    n, tps, dur, tr = lsdtracks.tracks(b); k = [i for i in range(n) if tr[i][1] == "SBTD"][0]
    p = 0x40 + sum(t[5] for t in tr)
    while p < len(b):
        t, _, seq, nb = struct.unpack_from("<HHII", b, p)
        if t == k:
            s = p + 16; nl = struct.unpack_from("<h", b, s)[0]; lt = struct.unpack_from("<I", b, s + 0x14)[0]; assert nl == len(times)
            for i, (a, e) in enumerate(times): struct.pack_into("<ff", b, s + lt + i * 0x20 + 0x14, max(0.0, a), max(0.0, e))
            return
        p += 16 + nb * 16

def graft_sbtd(b, s, times):
    """Put subtitle pack s (US) into b's SBTD packet with new times; False when it does not fit."""
    n, tps, dur, tr = lsdtracks.tracks(b); k = [i for i in range(n) if tr[i][1] == "SBTD"][0]
    s = bytearray(s.rstrip(b"\0") + b"\0" * 16); s = s[:len(s) - len(s) % 16] if len(s) % 16 else s
    nl = struct.unpack_from("<h", s, 0)[0]; lt = struct.unpack_from("<I", s, 0x14)[0]; assert nl == len(times)
    for i, (a, e) in enumerate(times): struct.pack_into("<ff", s, lt + i * 0x20 + 0x14, max(0.0, a), max(0.0, e))
    p = 0x40 + sum(t[5] for t in tr)
    while p < len(b):
        t, _, seq, nb = struct.unpack_from("<HHII", b, p)
        if t == k:
            if len(s) > nb * 16: return False
            b[p + 16:p + 16 + nb * 16] = bytes(s) + bytes(nb * 16 - len(s)); return True
        p += 16 + nb * 16

def reencode(dc_stream, dc_rate, total, name):
    x = L.decode(dc_stream, name)
    if dc_rate != 48000: x = resample_poly(x, 48000 // 300, dc_rate // 300, axis=0)
    cap = total // 2 // 16 * 28; x = np.clip(np.round(x[:cap]), -32768, 32767).astype("<i2")
    raw, out = os.path.join(L.TMP, name + "_48.raw"), os.path.join(L.TMP, name + "_enc.pcms")
    open(raw, "wb").write(x.tobytes()); subprocess.run([L.CODEC, "encode", raw, out, str(total)], check=True, capture_output=True)
    return open(out, "rb").read(), (len(x) + 27) // 28 * 16

def build(d, out):
    us, dc = isoset.Disc("us" + d), isoset.Disc("dc" + d); log = {}
    for p in sorted(q for q in us.tbl if q.endswith(".LSD")):
        ub = bytearray(us.read(p)); db = bytearray(dc.read(p))
        if p == "OPENING/DEMO.LSD":
            new, how = db, "dc opening movie"
        else:
            if not [t for t in lsdtracks.tracks(ub)[3] if t[1] == "PCMS"]: continue
            ku, hu, totu = pcms_hdr(ub); kd, hd, totd = pcms_hdr(db)
            ru, lu = struct.unpack_from("<HI", ub, hu + 0x26); rd, ld = struct.unpack_from("<HI", db, hd + 0x26)
            secs_u, secs_d = lu / 16 * 28 / ru, ld / 16 * 28 / rd
            su, sd = L.sbtd(ub), L.sbtd(db)
            if abs(secs_u - secs_d) <= 0.3:
                new = bytearray(ub); stream = L.pcms(db)[2]
                room = len(L.pcms(ub)[2])
                if rd == ru:      # same rate: the Japanese stream is copied as-is, cut or padded with silent ADPCM pairs to the US size
                    assert room % 0x1000 == 0 and len(stream) % 0x1000 == 0
                    how = "swap" if len(stream) == room else "swap (%s by %.2f s)" % ("trimmed" if len(stream) > room else "padded", abs(len(stream) - room) / 2 / 16 * 28 / 48000)
                    stream = stream[:room] + bytes(max(0, room - len(stream))); valid = ld
                else: stream, valid = reencode(stream, rd, room, p.replace("/", "_")); how = "swap (re-encoded, 44.1 kHz -> 48 kHz)"
                put_pcms(new, stream); struct.pack_into("<I", new, hu + 0x28, min(valid, len(stream) // 2))
                if su and sd: set_times(new, match_times(su[2], sd[2])); how += ", subtitles retimed"
            else:
                new = bytearray(db); how = "dc file (US re-timed the scene by %.1f s)" % (secs_u - secs_d)
                if su and sd and graft_sbtd(new, su[0], match_times(su[2], sd[2])): how += ", US subtitles grafted"
                elif su and sd:   # the US subtitle pack (it carries its own glyphs) is too big for the DC packet: swap the audio instead
                    new = bytearray(ub); room = len(L.pcms(ub)[2]); stream = L.pcms(db)[2]
                    if rd == ru: stream, valid = stream[:room] + bytes(max(0, room - len(stream))), ld
                    else: stream, valid = reencode(stream, rd, room, p.replace("/", "_"))
                    put_pcms(new, stream); struct.pack_into("<I", new, hu + 0x28, min(valid, len(stream) // 2))
                    set_times(new, match_times(su[2], sd[2])); how = "swap, start-aligned (US re-timed by %.1f s; subtitles too big for the DC file)%s" % (secs_u - secs_d, "" if rd == ru else ", re-encoded, 44.1 kHz -> 48 kHz")
        o = os.path.join(out, *p.split("/")); os.makedirs(os.path.dirname(o), exist_ok=True); open(o, "wb").write(bytes(new))
        log[p] = how; print(d, p, how, flush=True)
    json.dump(log, open(os.path.join(out, "undub_disc%s.json" % d), "w"), indent=1)

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
