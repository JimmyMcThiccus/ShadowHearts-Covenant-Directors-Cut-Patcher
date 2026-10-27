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

def set_desc(sec, idx, text):
    """point entry idx of a description section {u32 offs[n] (offs[0] = 4n), NUL strings} at a newly appended string (count unchanged)"""
    n = struct.unpack_from("<I", sec, 0)[0] // 4; assert idx < n
    offs = [struct.unpack_from("<I", sec, 4 * i)[0] for i in range(n)]
    end = max(sec.index(b"\0", o) + 1 for o in offs)
    new = bytearray(sec[:end]); at = len(new); new += text.encode("ascii") + b"\0"; new += bytes(-len(new) % 4)
    struct.pack_into("<I", new, 4 * idx, at); sec[:] = new

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

def _mdt(cmd):
    """CMDMENU.MSD attach 13 (the .MDT): (attach table offset, attach offset, size); it must end the file."""
    sys.path.insert(0, os.path.dirname(__file__)); import msdfile
    ao, att = msdfile.attaches(bytes(cmd)); o, idn, sz = att[13]; assert o + sz == len(cmd), "attach 13 is not last"
    return ao, o, sz

def _chunk(m, ty):
    import msdfile; return [c for c in msdfile.chunks(m) if c[1] == ty][0]

def _append_text(cmd, co_abs, text, enc="ascii"):
    """append a NUL string at the end of the file (= end of attach 13) and return its pointer relative to the chunk at co_abs"""
    ao, o, sz = _mdt(cmd)
    at = len(cmd); cmd += text.encode(enc) + b"\0"; cmd += bytes(-len(cmd) % 4)
    struct.pack_into("<I", cmd, ao + 16 + 12 * 13 + 8, len(cmd) - o)
    return at - co_abs

def fix_profiles(cmd):
    """Personal > Profile is MDT chunk 63 (18 records, 7 pointers: name, name, -, -, text, text after the story turn, face).
    The US left Lenny (12) and Veronica (13) in Japanese, but its Library (chunk 21, NPCs) has official English for both: the DC
    profile text is the same as the DC Library text, so reuse the US Library name and long text."""
    import msdfile
    ao, o, sz = _mdt(cmd); m = bytes(cmd[o:o + sz])
    lco, _, lpc, _, lstride, _, _ = _chunk(m, 21); pco, _, ppc, _, pstride, pcount, _ = _chunk(m, 63)
    assert (lpc, lstride, ppc, pstride, pcount) == (30, 0x80, 7, 0x20, 18)
    lib = lambda r, k: msdfile.cstr(m, lco + struct.unpack_from("<I", m, lco + 16 + r * lstride + 4 * k)[0]).decode("ascii")
    for prof, npc, name in ((12, 4, "Lenny Curtis"), (13, 9, "Veronica Vera")):
        rec = o + pco + 16 + prof * pstride
        assert msdfile.cstr(cmd, o + pco + struct.unpack_from("<I", cmd, rec)[0]).decode("cp932").startswith(("レニ", "ベロニカ"))
        assert lib(npc, 0) == name
        pn = _append_text(cmd, o + pco, name); pt = _append_text(cmd, o + pco, lib(npc, 6))
        struct.pack_into("<4I", cmd, rec, pn, pn, *struct.unpack_from("<2I", cmd, rec + 8))
        struct.pack_into("<2I", cmd, rec + 16, pt, pt)

# Library monsters the US cut (Director's Cut CMDMENU.MDT chunk 22): monster id -> (note, Library text).  The US battle code
# already sets their "defeated" bits (MON_ +0x14 bit 6 is clear for all ten), only the Library records were missing.
LIB_MONSTERS = {
    223: ("Demon born when a girl and a crow fused together.",          # Baphemetous
          "Born when a girl and a$crow, sacrificed to an$evil god, fused as one.$It drinks every fluid in$the human body. On a$whim it becomes a beauty$or a ram, claws and all."),
    222: ("High demon that absorbs humans to extend its own life.",     # Luvar
          "A high demon near the$top of Hell's hierarchy.$By absorbing humans, it$can live for millennia.$Many famous people who$died mysteriously still$live on as its flesh."),
    221: ("Two-headed snake with a venom fang and a cure fang.",        # Amphisbaena
          "A two-headed viper from$Ethiopian folklore. Its$right head's venom kills$any foe it bites. But if$the foe weeps and begs$for mercy, the left head$bites to cure the venom."),
    220: ("Loyal watchdog that serves an evil god.",                    # Nuckelavee
          "The evil god's faithful$hound. Long ago, it was$flayed for betraying the$high god. Unable to bear$fresh water, it lives in$the sea, and salt water$burns it every day."),
    219: ("Maggot spirit born from an executed villain's corpse.",      # Tsunemoto Bug
          "Maggot spirit that rose$from the corpse of the$villain Tsunemoto, put$to death some 400 years$ago. Millions swarmed$out, and the execution$ground drowned in them."),
    218: ("Plague god that brings every kind of epidemic.",             # Hosojin
          "A plague god who spreads$smallpox and many other$diseases. It also knows$how to cure any illness,$and demands sake, women$and offerings in return$for curing its own work."),
    217: ("Vengeful foot soldier's ghost that possesses flies.",        # Itsumade
          "The soul of a slain foot$soldier, possessing the$flies that feed on dead$flesh. \"How long must I$lie here?\" it wails. If$it sees your face, it$stalks you till mourned."),
    216: ("Ant grown gigantic from spiritual power.",                   # Futsutachi
          "A futsutachi is a beast$that lived for centuries$and took the shape it$wished. This ant, once$nearly burned under a$magnifier, grew huge out$of spite to eat humans."),
    215: ("Indian demon that infests the brains of cattle.",            # Rasetsu
          "A demon that infests the$brain of a cow and takes$over its body. Banished$from India for defiling$the cow, a sacred Hindu$animal, it drives its$host past all limits."),
    214: ("The seven gods of fortune, tainted by Malice.",              # 7 Gods of Luck
          "The Seven Gods of Luck,$tainted by the Malice$they absorbed. Their$seven blessings became$seven curses. If their$last reason fails, Japan$will drown in Malice."),
}

def fix_skill_titles(cmd):
    """MDT chunk 48 = the header of each special-skill list (stride 0xc: title pointer, then {u16 kind, s16 group, u16 index, u16 flags}).
    The US left 12 (Lenny, DC アイアンクロー) and 13 (Veronica, DC パニッシュ) empty; use their command names."""
    ao, o, sz = _mdt(cmd); m = bytes(cmd[o:o + sz]); co, ty, pc, base, stride, count, nxt = _chunk(m, 48)
    assert (pc, stride, count) == (1, 0xc, 40)
    for rec, text in ((12, "Iron Claw"), (13, "Punish")):
        r = o + co + 16 + rec * stride; p = struct.unpack_from("<I", cmd, r)[0]
        assert cmd[o + co + p] == 0 and struct.unpack_from("<h", cmd, r + 6)[0] == rec, rec    # empty title, group = rec
        struct.pack_into("<I", cmd, r, _append_text(cmd, o + co, text))

def append_records(cmd, ty, recs):
    """Grow MDT chunk `ty` in place by appending records [(strings per pointer (None = 0), tail bytes)]; the strings go into the
    chunk's own pool.  Every later chunk and the attach shift (their pointers are chunk-relative), so run before end-of-file appends."""
    ao, o, sz = _mdt(cmd); m = bytes(cmd[o:o + sz])
    co, t, pc, base, stride, count, nxt = _chunk(m, ty)
    rec_end = 16 + count * stride; grow = len(recs) * stride; new_end = rec_end + grow
    pool = bytearray(m[co + rec_end:co + nxt]); out = []
    for r in range(count):
        raw = bytearray(m[co + 16 + r * stride:co + 16 + (r + 1) * stride]); ps = struct.unpack_from("<%dI" % pc, raw)
        struct.pack_into("<%dI" % pc, raw, 0, *[p + grow if p >= rec_end else p for p in ps]); out.append(bytes(raw))
    for strs, tail in recs:
        ps = []
        for s in strs:
            if s is None: ps.append(0); continue
            ps.append(new_end + len(pool)); pool += s.encode("ascii") + b"\0"
        assert len(ps) == pc and len(tail) == stride - 4 * pc
        out.append(struct.pack("<%dI" % pc, *ps) + tail)
    while (new_end + len(pool)) % 16 != nxt % 16: pool.append(0)                            # later chunks keep their alignment
    head = bytearray(m[co:co + 16]); struct.pack_into("<I", head, 8, count + len(recs)); struct.pack_into("<I", head, 12, new_end + len(pool))
    nm = m[:co] + bytes(head) + b"".join(out) + bytes(pool) + m[co + nxt:]
    cmd[o:] = nm; struct.pack_into("<I", cmd, ao + 16 + 12 * 13 + 8, len(nm))

def add_help_specials(cmd, dc_cmd):
    """MDT chunk 19 = Help pages (stride 0x24: title + 5 pages + 1 pointer, then 8 tail bytes).  The DC appends #128 アイアンクロー and
    #129 パニッシュメント, and the Personal screen's top-left heading for Lenny's / Veronica's special-skill page is that Help title:
    with only 128 US pages it showed unrelated titles ("Soul Energy", "Game Over").  Append both, translated, with the DC's tails."""
    _, do_, dsz = _mdt(dc_cmd); dm = bytes(dc_cmd[do_:do_ + dsz]); dco, _, dpc, _, dstride, dcount, _ = _chunk(dm, 19)
    ao, o, sz = _mdt(cmd); co, _, pc, _, stride, count, _ = _chunk(bytes(cmd[o:o + sz]), 19)
    assert (pc, stride, count, dpc, dstride, dcount) == (7, 0x24, 128, 7, 0x24, 130)
    tails = [dm[dco + 16 + r * dstride + 4 * dpc:dco + 16 + (r + 1) * dstride] for r in (128, 129)]
    pages = (("Iron Claw", "Lenny's Special Ability.$The Steel Claws that Lenny summons$slash at the enemy all at once."),
             ("Punish", "Veronica's Special Ability.$With her special aroma oils and magic,$she brings pain to enemies and healing$to her allies."))
    for (title, text), tail in zip(pages, tails):
        assert all(len(l) <= 40 for l in text.split("$"))
    append_records(cmd, 19, [([title, text, "", "", "", "", None], tail) for (title, text), tail in zip(pages, tails)])

def add_library_monsters(cmd, dc_cmd):
    """Insert the ten DC-only monster records into MDT chunk 22 (Library > Monsters) in the DC's order, renumbering every record.
    Records: 18 chunk-relative pointers (reading, note, text, model view block, motion names) then {u8, u8 ids<<3|flags, s16 ids[6],
    u16 number}.  CmdLibrary and CmdLibraryList take the count from the chunk header and allocate per record (FIELD.BIN 0x49c6b0).
    The chunk grows in place, so every later chunk and the attach shift (their pointers are chunk-relative); run this before
    anything is appended to the end of the file."""
    import msdfile
    ao, o, sz = _mdt(cmd); m = bytes(cmd[o:o + sz])
    co, ty, pc, base, stride, count, nxt = _chunk(m, 22)
    _, do_, dsz = _mdt(dc_cmd); dm = bytes(dc_cmd[do_:do_ + dsz])
    dco, _, dpc, _, dstride, dcount, _ = _chunk(dm, 22)
    assert (pc, stride, count, dpc, dstride, dcount) == (18, 0x58, 175, 18, 0x58, 185)
    rec = lambda mm, c, i: mm[c + 16 + i * stride:c + 16 + (i + 1) * stride]
    first_id = lambda r: struct.unpack_from("<h", r, 0x4a)[0]
    grow = (dcount - count) * stride; rec_end = 16 + count * stride; new_rec_end = 16 + dcount * stride
    pool = bytearray(m[co + rec_end:co + nxt])
    def find(s):                                       # an existing NUL-terminated string in the US pool -> new pointer
        k = s + b"\0"; i = pool.find(k)
        while i > 0 and pool[i - 1] != 0: i = pool.find(k, i + 1)
        return None if i < 0 else new_rec_end + i
    empty = find(b""); assert empty is not None
    def put(data, align=1, phase=0):
        while (new_rec_end + len(pool)) % align != phase: pool.append(0)
        p = new_rec_end + len(pool); pool.extend(data); return p
    us = iter(rec(m, co, i) for i in range(count)); out = []
    for i in range(dcount):
        d = rec(dm, dco, i); mid = first_id(d)
        if mid not in LIB_MONSTERS:
            r = bytearray(next(us)); assert first_id(r) == mid, (i, mid, first_id(r))
            ps = struct.unpack_from("<18I", r); assert min(ps) >= rec_end
            struct.pack_into("<18I", r, 0, *[p + grow for p in ps])
        else:
            note, text = LIB_MONSTERS[mid]
            assert len(note) <= 56 and text.count("$") <= 6 and max(len(l) for l in text.split("$")) <= 24, mid
            dps = struct.unpack_from("<18I", d); ps = [empty, put(note.encode("ascii") + b"\0"), put(text.encode("ascii") + b"\0")]
            ps.append(put(dm[dco + dps[3]:dco + dps[3] + 16], 16, dps[3] % 16))           # model view block (4 floats), same phase
            for p in dps[4:]:
                s = msdfile.cstr(dm, dco + p); q = find(s); ps.append(q if q is not None else put(s + b"\0"))
            r = bytearray(struct.pack("<18I", *ps) + d[0x48:])
        struct.pack_into("<H", r, 0x56, i); out.append(bytes(r))
    assert next(us, None) is None
    while (len(pool) + new_rec_end) % 16 != (nxt % 16): pool.append(0)                     # later chunks keep their alignment
    head = bytearray(m[co:co + 16]); struct.pack_into("<I", head, 8, dcount); struct.pack_into("<I", head, 12, new_rec_end + len(pool))
    nm = m[:co] + bytes(head) + b"".join(out) + bytes(pool) + m[co + nxt:]
    cmd[o:] = nm
    struct.pack_into("<I", cmd, ao + 16 + 12 * 13 + 8, len(nm))

# Attacks of the ten DC monsters (SKIL group 0x19 records 481-523, all on name 37 "Unknown" in the US).  MONSTERParam +0x16/+0x18 =
# two attack ids, or -1 and a skill set (group 0x18): 214 set 74, 215-220 sets 80..75, 221-223 singles.  Every name except the Seven
# Gods' own is shared with US monsters, so it takes the official US name (DC and US name indices paired through the shared records).
SEVEN_GODS_ATTACKS = ["Path to Yomi", "Pure Integrity", "Contentment", "Great Majesty",     # 黄泉路照 清廉潔白 少欲知足 大いなる威光
                      "Alms Giving", "Charming Face", "Divine Virtue", "One Ailment"]        # 喜捨奨励 愛敬の相 神徳 一病息災
DC_MONSTER_ATTACKS = dict(zip(range(481, 489), SEVEN_GODS_ATTACKS))                         # 214 7 Gods of Luck
DC_MONSTER_ATTACKS.update({
    489: "Spec. Def. Down", 490: "Dark Claw",                                                # 223 Baphemetous
    491: "Mental Break", 492: "Magma",                                                       # 222 Luvar
    493: "Phys. Atk. Down", 494: "Rock Storm",                                               # 221 Amphisbaena
    495: "Blind Ring", 496: "Dark Claw", 497: "Slash", 498: "Red Blaze", 499: "Surge",        # 220 Nuckelavee
    500: "Slow", 501: "Arc Gale", 502: "Magma", 503: "Red Cradle",                           # 219 Tsunemoto Bug
    504: "Phys. Atk. Down", 505: "Arc Shield", 506: "Rock Strike", 507: "Thorn", 508: "Gathering",       # 218 Hosojin
    509: "Spec. Atk. Down", 510: "Arc Barrier", 511: "Slash", 512: "Gale Spike", 513: "Gathering",      # 217 Itsumade
    514: "Dying", 515: "Entrance", 516: "Splash", 517: "Hail Crash", 518: "Gathering",                  # 216 Futsutachi
    519: "SP Lowering", 520: "Energy Charge", 521: "Nova", 522: "Bright Banish", 523: "Gathering"})     # 215 Rasetsu
assert len(DC_MONSTER_ATTACKS) == 43 and all(len(t) < 18 for t in SEVEN_GODS_ATTACKS)

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
    skil += bytes(18 * len(SEVEN_GODS_ATTACKS))                          # names 185.. for the Seven Gods of Luck's own attacks
    for k, text in enumerate(SEVEN_GODS_ATTACKS): rec18(skil, 185 + k, text)
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
    # accessory 34: Carla's thanks for the Adriatic Magnolia (FI_00_U gives code 1314 in both versions).  US and DC alike name it with a
    # placeholder ("Unknown" / ダウン系防御, note 未定) and its record has no effects, so it gets an honest name instead of a made-up effect
    charm = (add_name(b"ACS_", "Magnolia Charm"), add_desc(sec_desc(b"ACS_"), "A thank-you gift from Carla. It has no effect."))
    # battle help notes the US left as "Unknown" / "Unkown" (SKIL notes 53/54 stay, other cut skills use them): DC-party specials and
    # Nicolai's Divine Light, worded like the US notes.  (group, skill) -> note index, set in SSHDAT below
    skill_notes = {(gr, k): add_desc(sec_desc(b"SKIL"), text) for (gr, k), text in (
        ((11, 2), "Light Class Special Damage. Circular, medium/4 hits/%i86"),      # ディバインライト
        ((12, 0), "Non-class Physical Damage. Single/5 hits/%i97"),                  # アイアンクロー
        ((13, 0), "Recovers Status, Ring Abnormalities for one ally."),              # ヒール
        ((13, 1), "Water Class Special Damage. Piercing, small/2 hits/%i70"),        # ヘイルビーク
        ((13, 2), "Water Special Dmge. + Paralysis. Circ., medium/10 hits/%i70"))}   # スタンパフューム
    # BM_N 24 = help line of Veronica's Punish command (the US dropped the DC's placeholder 24, so its 24 is the DC's 25)
    bmn = secs[tags.index(b"BM_N")]; o = struct.unpack_from("<I", bmn, 4 * 24)[0]; assert bmn[o:bmn.index(b"\0", o)] == b"Unknown"
    set_desc(bmn, 24, "Use aroma oils and magic to cause pain or heal.")             # アロマオイルと魔法の力で、痛みといやしを与えます。
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
    r = 34 * 44; assert struct.unpack_from("<HH", acs, r) == (34, 0x1c) and struct.unpack_from("<h", acs, r + 0x28)[0] == -1
    assert struct.unpack_from("<I", acs, r + 0xc)[0] == 0                                  # effect count 0: it really does nothing
    struct.pack_into("<H", acs, r + 2, charm[0]); struct.pack_into("<H", acs, r + 0x28, charm[1])
    clot = secs[12]; assert len(clot) == 124                                           # 10 records of 12 bytes + 4-byte trailer
    clot[120:120] = struct.pack("<6H", 10, 10, 0x43, 0x406, 10, 0)                     # DC record: model 0x43 (FIELD/MODEL/067), flags 0x406
    key = secs[11]; r = 103 * 16; assert struct.unpack_from("<2H", key, r) == (103, 0xffff)        # the US zeroed this record; DC layout:
    struct.pack_into("<8H", key, r, 103, thief[0], 0xffff, 0xffff, 0xffff, 0xffff, thief[1], 0)   # {id, name, -1 x4, note, 0}
    sk = secs[13]
    off, cnt = struct.unpack_from("<II", sk, 0x19 * 8); assert cnt == 524                   # monster attacks: 0x20-byte records, +2 name
    for sid, text in DC_MONSTER_ATTACKS.items():
        p = off + sid * 0x20 + 2; assert struct.unpack_from("<H", sk, p)[0] == 37, sid
        idx = 185 + SEVEN_GODS_ATTACKS.index(text) if sid <= 488 else find18(skil, text)
        struct.pack_into("<H", sk, p, idx)
    for (gr, k), idx in skill_notes.items():
        p = struct.unpack_from("<I", sk, gr * 8)[0] + k * 0x40 + 0x3e; assert struct.unpack_from("<h", sk, p)[0] in (53, 54), (gr, k)
        struct.pack_into("<h", sk, p, idx)
    off, cnt = struct.unpack_from("<II", sk, 13*8); assert cnt == 3
    for j, idx in ((0, 184), (1, 182), (2, 183)):
        assert struct.unpack_from("<h", sk, off + j*0x40 + 2)[0] == 37
        struct.pack_into("<h", sk, off + j*0x40 + 2, idx)
    dat = regbuild(head, tags, secs)
    # --- menu scenes ---
    per = bytearray(us.read("MENU/MSD/PERSONAL.MSD"))
    same_len(per, "アイアンクロー", "Iron Claw"); same_len(per, "レニの個有技を表示します。", "View Lenny's techniques.")
    same_len(per, "パニッシュ", "Punish"); same_len(per, "ベロニカの個有技を表示します。", "View Veronica's techniques.")
    import personal_titles; personal_titles.apply(per, us)    # top-left page titles: "Iron Claw" / "Punish" (US had Soul Energy / Game Over)
    cmd = bytearray(us.read("MENU/DAT/CMDMENU.MSD"))
    same_len(cmd, "アイアンクロー", "Iron Claw"); same_len(cmd, "パニッシュメント", "Punishment")
    dc_cmd = isoset.Disc("dc1").read("MENU/DAT/CMDMENU.MSD")
    add_library_monsters(cmd, dc_cmd)                 # grows chunk 22 in place: before any appends
    add_help_specials(cmd, dc_cmd)                    # grows chunk 19 in place: before any appends
    fix_profiles(cmd); fix_skill_titles(cmd)
    # Azure Orb's Triangle "Explanation" text (DC: マリスを吸収する力を持つ謎の宝珠。…苦しみ呻く人面のようなものが映っている。)
    add_item_explain(cmd, 41, "A mysterious orb that can absorb Malice.$It normally glows a pale blue, but when$it absorbs Malice it shines blood red.$Look closely to see anguished faces.")
    # DC: 山伏が悪霊を調伏する際に用いる霊的補助具。耳飾の中には、悪霊の魔力を吸い取る大粒の岩塩…獲得ソウルエナジーが増加する。
    add_item_explain(cmd, 53, "Used by mountain ascetics to subdue$evil spirits. Each holds a lump of rock$salt that drains a spirit's power. More$Soul Energy is gained in battle.", chunk=12)
    add_item_explain(cmd, 34, "A little charm Carla gave as thanks for$fetching the Adriatic Magnolia. It is$pretty to look at, but it has no effect$in battle.", chunk=12)
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
