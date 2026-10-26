import struct, sys
AL = "\0.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
def decode(k):
    w0, l0, l1, l2 = struct.unpack(">4H", k)
    his = [w0 % 40, (w0 // 40) % 40, w0 // 1600]
    s = ""
    for hi, lo in zip(his, (l0, l1, l2)):
        u = (hi << 16) | lo
        for _ in range(4):
            d = u % 40; u //= 40
            if d: s += AL[d]
    return s
def load(path):
    b = open(path, "rb").read()
    n = struct.unpack_from("<H", b, 0)[0]
    E = []
    for i in range(n):
        o = 16 + i*16
        off, sz = struct.unpack_from("<II", b, o+8)
        E.append((decode(b[o:o+8]), off, sz))
    isdir = lambda e: e[2] & 0x80000000
    cd = lambda e: (e[2] & 0x7fffffff) // 16
    out = {}
    def walk_list(start, limit, prefix, base):
        end = start; fc = None
        while end < min(limit, n):
            e = E[end]
            if isdir(e) and fc is None: fc = start + cd(e)
            end += 1
            if fc is not None and end >= fc: break
        idx = list(range(start, end))
        for k, i in enumerate(idx):
            e = E[i]; p = prefix + "/" + e[0]; off = base + e[1]*16
            if isdir(e):
                nxt = next((start + cd(E[j]) for j in idx[k+1:] if isdir(E[j])), limit)
                walk_list(start + cd(e), nxt, p, off)
            else:
                out[p] = (e[2], off)
    root_end = next(cd(e) for e in E if isdir(e))
    for k in range(root_end):
        e = E[k]
        if isdir(e):
            nxt = next((cd(x) for x in E[k+1:root_end] if isdir(x)), n)
            walk_list(cd(e), nxt, e[0], 0)
        else:
            out[e[0]] = (e[2], 0)
    return out
if __name__ == "__main__":
    for p in sys.argv[1:]:
        d = load(p)
        print(p, len(d))
def load_bytes(b):
    import tempfile, os
    fd, p = tempfile.mkstemp(); os.write(fd, b); os.close(fd)
    try: return load(p)
    finally: os.remove(p)
