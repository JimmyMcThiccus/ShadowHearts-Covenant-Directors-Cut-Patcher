"""US data fixes for the Director's Cut party (Nicolai / Lenny / Veronica), written to OVR_DIR mirroring disc paths.
usage: patch_data.py OVR_DIR"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__)); import isoset

def regfile(b):
    n, tot = struct.unpack_from("<II", b, 0)
    tags = [b[8 + i*8:12 + i*8] for i in range(n)]; offs = [struct.unpack_from("<I", b, 12 + i*8)[0] for i in range(n)] + [tot]
    return b[:offs[0]], tags, [bytearray(b[offs[i]:offs[i+1]]) for i in range(n)]

def regbuild(head, tags, secs):
    head = bytearray(head); off = len(head)
    for i, s in enumerate(secs):
        struct.pack_into("<4sI", head, 8 + i*8, tags[i], off); off += len(s)
    struct.pack_into("<I", head, 4, off)
    return bytes(head) + b"".join(bytes(s) for s in secs)

def rec18(sec, i, text=None):
    if text is None: return bytes(sec[i*18:i*18+18]).split(b"\0")[0]
    t = text.encode("ascii"); assert len(t) < 18, text
    sec[i*18:i*18+18] = t + bytes(18 - len(t))

def find18(sec, text):
    for i in range(len(sec) // 18):
        if rec18(sec, i) == (text if isinstance(text, bytes) else text.encode()): return i
    raise KeyError(text)

def add_desc(sec, text):
    """append a string to a description section {u32 offs[n] (offs[0] = 4n), NUL strings}; returns its index"""
    n = struct.unpack_from("<I", sec, 0)[0] // 4
    offs = [struct.unpack_from("<I", sec, 4 * i)[0] for i in range(n)]
    pool = bytes(sec[4 * n:]); end = max(pool.index(b"\0", o - 4 * n) + 1 for o in offs)
    pool = pool[:end]
    new = struct.pack("<%dI" % (n + 1), *([o + 4 for o in offs] + [4 * (n + 1) + len(pool)])) + pool + text.encode("ascii") + b"\0"
    new += bytes(-len(new) % 4)
    sec[:] = new
    return n

def add_item_explain(cmd, item, text, chunk=13, width=40, lines=4, copy_ptrs=()):
    """CMDMENU.MSD: attach 13 is the .MDT of item/equipment texts; chunk type 13 = items, 12 = accessories, 23 = key items (records
    of chunk-relative text pointers: reading, explanation, ...).  The attach ends at the end of the file, so the text is appended
    there and the attach grows (attach table rows {u32 offset, u32 id, u32 size})."""
    sys.path.insert(0, os.path.dirname(__file__)); import msdfile
    ao, att = msdfile.attaches(bytes(cmd)); o, idn, sz = att[13]; assert o + sz == len(cmd), "attach 13 is not last"
    m = bytes(cmd[o:o + sz]); co, ty, pc, base, stride, count, nxt = [c for c in msdfile.chunks(m) if c[1] == chunk][0]
    assert pc >= 2 and item < count, (chunk, pc, count)
    rec = o + co + 16 + item * stride
    t = text.encode("ascii"); assert max(len(l) for l in t.split(b"$")) <= width and t.count(b"$") <= lines - 1, text
    for k, src in copy_ptrs:                                        # e.g. the costume face motion: reuse another record's pointer
        struct.pack_into("<I", cmd, rec + 4 * k, struct.unpack_from("<I", cmd, o + co + 16 + src * stride + 4 * k)[0])
    at = len(cmd); cmd += t + b"\0"; cmd += bytes(-len(cmd) % 4)
    struct.pack_into("<I", cmd, rec + 4, at - (o + co))             # pointer 1 = explanation, relative to the chunk
    struct.pack_into("<I", cmd, ao + 16 + 12 * 13 + 8, len(cmd) - o)

def same_len(blob, jp, en, enc="cp932"):
    """Replace a NUL-terminated string in a packed pool keeping its byte length (pad with spaces, no new NULs)."""
    k = jp.encode(enc) + b"\0"; i = blob.find(k); assert i >= 0 and blob.find(k, i + 1) < 0, jp
    e = en.encode("ascii"); assert len(e) <= len(k) - 1, (jp, en)
    blob[i:i + len(k) - 1] = e + b" " * (len(k) - 1 - len(e))

def main(out):
    us = isoset.Disc("us1")
    # --- SSHMES.NA ---
    head, tags, secs = regfile(us.read("COMMON/SSHMES.NA"))
    for s in secs:                                    # "Rene" -> "Lenny" (PC_N + DEMO presets, 16/18-byte name fields)
        k = s.find(b"\0\0Rene\0")
        while k >= 0:
            s[k+2:k+8] = b"Lenny\0"; k = s.find(b"\0\0Rene\0", k + 1)
    skil = secs[[t for t in tags].index(b"SKIL")]     # first SKIL = names (18-byte records)
    assert rec18(skil, 36) == b"Iron Clow" and rec18(skil, 37) == b"Unknown" and len(skil) // 18 == 182
    # 37 "Unknown" stays: the US also shows it for the cut DC monsters' attacks (renaming it made every Shichifukujin attack "Heal")
    rec18(skil, 36, "Iron Claw")
    skil += bytes(54); rec18(skil, 182, "Hail Break"); rec18(skil, 183, "Stun Perfume"); rec18(skil, 184, "Heal")
    # Azure Orb (ITEM 41, Sea of Woods): the US kept only its name; give it a description (DC: 薄青い輝きを放つ宝珠。)
    item_desc = [i for i, t in enumerate(tags) if t == b"ITEM"][1]
    azure_desc = add_desc(secs[item_desc], "An orb that glows a pale blue.")
    bmi = secs[tags.index(b"BM_I")]
    rec18(bmi, find18(bmi, b"Clow"), "Iron Claw"); rec18(bmi, find18(bmi, b"Panish"), "Punish")
    # DC-only accessory 53 (山伏の耳輪, prize of the WI_12_U / WI_13_U minigames, shows as "Unknown" in the US) and key item 103
    # (義賊の魂, Louis Mandrin's tools): names + notes appended, indices set in SSHDAT below
    def add_name(tag, text):
        sec = secs[[i for i, t in enumerate(tags) if t == tag][0]]; n = len(sec) // 18
        sec += bytes(18); rec18(sec, n, text); return n
    sec_desc = lambda tag: secs[[i for i, t in enumerate(tags) if t == tag][1]]
    earring = (add_name(b"ACS_", "Ascetic Earrings"), add_desc(sec_desc(b"ACS_"), "Soul Energy gained increases 20%."))
    thief = (add_name(b"KEYI", "Noble Thief Soul"), add_desc(sec_desc(b"KEYI"), "Tools of the 18th-century noble thief Louis Mandrin."))
    # costume 10 美しき愚者 (Beautiful Fool, Pierre's reward for the Mr. Meiyuan card): name 10 and note 10 (looked up by costume id)
    assert add_name(b"CLOT", "Beautiful Fool") == 10 and add_desc(sec_desc(b"CLOT"), "Cornelia's dress. Non-class. Lowers all attacks.") == 10
    mes = regbuild(head, tags, secs)
    # --- SSHDAT.NA: Veronica's skills 2/3 (party group 13) -> the appended names ---
    head, tags, secs = regfile(us.read("COMMON/SSHDAT.NA"))
    it = secs[10]; assert struct.unpack_from("<h", it, 41 * 48 + 0x22)[0] == -1     # ITEM record 41 = Azure Orb, +0x22 = description index
    struct.pack_into("<h", it, 41 * 48 + 0x22, azure_desc)
    acs = secs[9]; r = 53 * 44; assert struct.unpack_from("<HH", acs, r) == (53, 0x1c) and struct.unpack_from("<h", acs, r + 0x28)[0] == -1
    struct.pack_into("<H", acs, r + 2, earring[0]); struct.pack_into("<H", acs, r + 0x28, earring[1])
    clot = secs[12]; assert len(clot) == 124                                           # 10 records of 12 bytes + 4-byte trailer
    clot[120:120] = struct.pack("<6H", 10, 10, 0x43, 0x406, 10, 0)                     # DC record: model 0x43 (FIELD/MODEL/067), flags 0x406
    key = secs[11]; r = 103 * 16; assert struct.unpack_from("<2H", key, r) == (103, 0xffff)        # the US zeroed this record; DC layout:
    struct.pack_into("<8H", key, r, 103, thief[0], 0xffff, 0xffff, 0xffff, 0xffff, thief[1], 0)   # {id, name, -1 x4, note, 0}
    sk = secs[13]; off, cnt = struct.unpack_from("<II", sk, 13*8); assert cnt == 3
    for j, idx in ((0, 184), (1, 182), (2, 183)):
        assert struct.unpack_from("<h", sk, off + j*0x40 + 2)[0] == 37
        struct.pack_into("<h", sk, off + j*0x40 + 2, idx)
    dat = regbuild(head, tags, secs)
    # --- menu scenes ---
    per = bytearray(us.read("MENU/MSD/PERSONAL.MSD"))
    same_len(per, "アイアンクロー", "Iron Claw"); same_len(per, "レニの個有技を表示します。", "View Lenny's techniques.")
    same_len(per, "パニッシュ", "Punish"); same_len(per, "ベロニカの個有技を表示します。", "View Veronica's techniques.")
    cmd = bytearray(us.read("MENU/DAT/CMDMENU.MSD"))
    same_len(cmd, "アイアンクロー", "Iron Claw"); same_len(cmd, "パニッシュメント", "Punishment")
    # Azure Orb's Triangle "Explanation" text (DC: マリスを吸収する力を持つ謎の宝珠。…苦しみ呻く人面のようなものが映っている。)
    add_item_explain(cmd, 41, "A mysterious orb that can absorb Malice.$It normally glows a pale blue, but when$it absorbs Malice it shines blood red.$Look closely to see anguished faces.")
    # DC: 山伏が悪霊を調伏する際に用いる霊的補助具。耳飾の中には、悪霊の魔力を吸い取る大粒の岩塩…獲得ソウルエナジーが増加する。
    add_item_explain(cmd, 53, "Used by mountain ascetics to subdue$evil spirits. Each holds a lump of rock$salt that drains a spirit's power. More$Soul Energy is gained in battle.", chunk=12)
    # DC: １８世紀の義賊、ルイ・マンドランが愛用した仕事道具。百年以上前の物だが、子孫が大事に手入れを続けてきたため…
    # DC: デザイナーは時として、機能性を殺し、インパクトを追ってしまうこともある。そのリスクを背負うことを覚悟した本物の洒落者だけが…
    add_item_explain(cmd, 10, "Sometimes a designer$sacrifices function to$chase impact. Only a$true dandy, ready to$take that risk, may$wear this dress.", chunk=17, width=24, lines=7, copy_ptrs=((4, 9),))
    add_item_explain(cmd, 103, "Tools used by Louis Mandrin, the noble$thief of the 1700s. Over a century old,$but his descendants kept them so well$they are rust-free and ready to use.", chunk=23)
    for path, data in (("COMMON/SSHMES.NA", mes), ("COMMON/SSHDAT.NA", dat), ("MENU/MSD/PERSONAL.MSD", per), ("MENU/DAT/CMDMENU.MSD", cmd)):
        p = os.path.join(out, *path.split("/")); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(bytes(data))
        print("wrote", path, len(data))

if __name__ == "__main__":
    main(sys.argv[1])

def wmap_add_names(blob, names):
    """WORLDMAP/WMAPn.DAT bundle: u32 count, u32 total size, then per entry {u32 offset @12+8i, tag} (sh2_field::worldmap::bundle_entry).
    Entry 11 = point-name table {u16 count, u16 offs[count], NUL strings} of (name, reading) pairs; the DC adds point 45
    (Sea of Woods, JU_01_U) and the US table stops at 90 strings.  Grow entry 11 and shift every later entry."""
    n = struct.unpack_from("<I", blob, 0)[0]
    off = [struct.unpack_from("<I", blob, 12 + 8*i)[0] for i in range(n)]
    assert struct.unpack_from("<I", blob, 4)[0] == len(blob) and off == sorted(off)
    ends = off[1:] + [len(blob)]
    t = blob[off[11]:ends[11]]; cnt = struct.unpack_from("<H", t, 0)[0]; offs = list(struct.unpack_from("<%dH" % cnt, t, 2))
    raw = t[2 + cnt*2:]
    used = max(raw.index(b"\0", o) + 1 for o in offs)       # end of the last string any offset points into
    pool = bytearray(raw[:used])
    for s_ in names:
        offs.append(len(pool)); pool += s_.encode("ascii") + b"\0"
    nt = struct.pack("<H", len(offs)) + struct.pack("<%dH" % len(offs), *offs) + bytes(pool)
    nt += bytes(-len(nt) % 16)
    grow = len(nt) - len(t); assert grow % 16 == 0
    out = bytearray(blob[:off[11]]) + nt + blob[ends[11]:]
    for i in range(12, n): struct.pack_into("<I", out, 12 + 8*i, off[i] + grow)
    struct.pack_into("<I", out, 4, len(out))
    return bytes(out)
