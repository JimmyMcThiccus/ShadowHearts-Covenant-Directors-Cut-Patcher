# Director's Cut content -> US retail (work in progress)

Inputs: `..\Directors cut\*.iso` (SLPS_732.14, 2 discs), `..\US-Midway\*.iso` (SLUS_210.41/.44).  Outputs go to `..\dc_patch_test\`.

## Pipeline (disc 1 test build)
1. Extract scripts: tools read the ISOs directly (`iso.py`, `pkf.py`); DC scripts live in FIELD.PKB `FIELD/MPS/*.MSC`.
2. Translate: `python tools/apply_tr.py translations/ks_en.py <dc_msc_dir> out/` - appends English strings to each
   script's data segment and repoints the `0x15` operands (originals untouched); wraps to 40 cols x 3 lines.
3. Hook: `python tools/hook_ca02.py <us CA_02_U.MSC> <dc CA_02_U.MSC> out/CA_02_U.MSC` - appends the DC boat branch
   (Nahash on the first crossing to Sainte-Marguerite) as a new function and calls it from the US boat event.
4. Build: copy the US disc 1 ISO, then `python tools/inject2.py <copy.iso> <dc disc1.iso> <us disc2.iso> <out_tbl> out/`
   - appends all DC-only files (out/ overrides them), repoints existing US entries, rewrites PKFINFO.TBL at the end.
5. Live: boot the copy fresh (save states made on the original ISO hang on reads past the old disc end), load the
   debug-map save, `python tools/dclive.py warp KS_00_U`, then Circle+R3 > Experiment.

## Facts found (2026-10-24)
* US engine runs DC scripts unmodified (same 135 CField ops); DC battle data/monsters are already on the US discs.
* `GetFieldData(0x36)` = build id: DC 1, US 2.
* Typewriter captions (`callu 0x6246`): each slot must be <= ~3 chars or the rest of the line is dropped.
* DC hooks into US maps: CA_02_U -> KS_00_U (done), ND_04_A -> ND_11_U, ND_20_U -> ND_10_U (todo); JU/MS/_QUIZ/_9/_D variants
  are entered another way (todo).  Disc 2 needs the same treatment.

## Disc 2: N125 "The Promise" (DC pre-rendered movie, English audio)

The DC replaced the in-engine N125 (US: 23 tracks, Gy_07_u models) with a 512x448 MPEG-2 movie (`MOVS`, 7400 frames, 246.85 s). `GY_06_U` event 2 starts
it the same way in both builds (`MCES("N125.LSD", 281, ...)` while flag 698 is clear), so the file is swapped and no script changes.

1. `lsdtracks.py` lists the tracks. The audio is `PCMS` (stereo SPU-ADPCM at 48 kHz, L/R 0x800-byte chunks; per-channel bytes at hdr +0x28).
2. `pcmscodec` (Rust, `cargo build --release`): `decode IN.pcms OUT.raw` / `encode IN.raw OUT.pcms 13541376`. The encoder scores 39 dB SNR on non-ADPCM sources.
3. The English track is the user's WAV, conformed to the DC movie (frame 0 = movie start), trimmed to 11,848,704 frames, then encoded.
4. `lsd_swap_pcms.py DC_N125.LSD en.pcms N125.LSD` swaps the audio in place (same packet layout and size). Put it in the overrides as `LSD/N125.LSD`.
5. `inject2.py <US disc 2 copy> <DC disc 2> <US disc 1> <out.tbl> <overrides>`, as for disc 1.

Verified live (test 10 disc 2, played from the Theater): the movie plays and the English audio stays in sync to the end. The subtitles are still the DC's Japanese `SBTD`.
`theater_unlock.py` (at the title screen) sets common[1] and the 162 scene bits at 0x100000 and in TitleShared 0x45e940. N125 = Theater index 143, chapter 20.
`dclive.py replace OLD.iso NEW.iso` loads a whole disc table into RAM after a PCSX2 disc swap (the root entries hold absolute LBAs).
English captions: `lsd_swap_sbtd.py N125.LSD US_N125.sbtd times.json OUT.LSD` grafts the US subtitle pack (59 lines, its own font) into the DC
packet, padded to the DC size. The times come from matching each US line's stretch of US voice audio against the conformed English track:
search within ±1.5 s of the DC Japanese line's time, and fall back to the DC time when the match is weak. 56 of 59 lines matched; all are within 1.3 s of the DC timing. Built into disc 2 test 11.

## Shared-map DC scenes (test 14)

US scripts were changed during localisation, so DC scripts can't simply replace them. `graft.py` splices the DC-only blocks into the US
scripts: it adds `jmp` detours to appended code, copies or maps callees, adds events, and patches operands in place. Specs and translations are in
`translations/scenes/*.py`; build them with `graft_scene.py SPEC OUT`. Live presets are in `dcscene.py` (flags plus the debug warp) and `tp.py` (teleport).

| Scene | Maps | Trigger | Verified |
|---|---|---|---|
| Lucia & Veronica | MS_00_U -> GT_04_U -> GT_03_U | reg8[0x334]: 1 -> 99 -> 2 | test 14 |
| Anastasia's Fortune | FI_00_U | start, flag 75 set, 10719/7065 clear | test 13 |
| The Currymen | RE_03_U (+event 100) | flag 105 set, 9634 clear; talk to the NPCs | test 13 (re-check on 14) |
| Joachim in Japan | IN_00_U event 111 | first talk while 8413 clear | test 14 |
| Deeper into the Neam Ruins | ND_04_A -> ND_11..13 -> ND_10 -> ND_20_U | flag 620 (Anastasia subquest) | ND_04_A -> ND_11_U on test 14 |

The Ring Soul quizzes are already in the US release, so they aren't ported. **VM rule:** JobExec resets the operand stack after every
0x90-0x9f statement and at op01, so a detour may only jump back on a statement boundary (`Graft._patch_site`).

## Beautiful Fool costume (test 19)
- `WI_13_U.MSC`: DC event 4 replaces the US one (`translations/scenes/meiyuan.py`); with a Shadow Hearts 1 save, the minigame offers the Mr. Meiyuan card. The existing US PA_03_U event 25 then gives the dress.
- `patch_data.py`: CLOT record 10 (inserted before the 4-byte trailer), name, note, and the CMDMENU.MDT chunk 17 explanation (with the fac1 pointer copied from dress 9).
- `tools/patch_tailor.py OUT_DIR` writes `FIELD.BIN` and `SHOP/TAILOR.DAT`. The Change Dress list goes from 10 to 11 entries, the tailor object fields at >=0x14c shift +4, and the TAILOR.DAT slots shift by one around the inserted DC sketch page.
- The Change Dress screen takes its explanation from TAILOR.DAT's last `msg` entry ({u16 n=22, u16 offs[22], pool}: a reading and an explanation per dress), not from CMDMENU, so `patch_tailor.py` also fills dress 10 there (test 20).
- FIELD.BIN sits in the ISO root, not in a PKB, so write it in place at its LBA after inject2 (it is the same size and identical on both discs).

## Profile and Library (test 24)
- CMDMENU.MDT chunk 63 = Personal > Profile (7 pointers: name, name, -, -, text, text after the story turn, face). The US left records 12 (Lenny) and 13 (Veronica) in Japanese. `patch_data.fix_profiles` points them at copies of the US Library's own name and long text (chunk 21, NPC records 4 and 9).
- Chunk 22 = Library > Monsters (stride 0x58: 18 pointers, then {u8, u8 ids<<3|flags, s16 ids[6], u16 number}). The DC has 185 records and the US has 175; the missing ones are monsters 214-223. The kill bit (BTL0 +0xf43) is already set by the US battle code (MON_ +0x14 bit 6 is clear for all ten), and CmdLibrary / CmdLibraryList (FIELD.BIN 0x4996a0 / 0x49c6b0) take the count from the chunk header. `patch_data.add_library_monsters` inserts the ten DC records in the DC's order, with English text, the DC's view block and motion names, then renumbers everything. The chunk grows in place, so this runs before anything is appended to the end of CMDMENU.
- Not ported yet: chunk 19 (Help) has two DC-only pages for the Iron Claw and Punishment abilities.

## Monster attack names (test 25)
- The game looks up names with SLUS 0x3b9540(type, id, sub), which selects an SSHDAT section, stride and +2 name index, then an 18-byte SSHMES name. Monster attacks are type 9 sub 0x19: SKIL group 0x19, 0x20-byte records.
- MONSTERParam +0x16/+0x18 hold either two attack ids, or -1 and a skill set (group 0x18: 0x28-byte records of 20 s16).
- The DC monsters 214-223 use attacks 481-523, and the US points all of them at name 37 "Unknown". Name 37 has to stay "Unknown" for other cut content.
- `patch_data.DC_MONSTER_ATTACKS` points 35 of them at their official US names. DC and US name indices are paired through the skill records both versions share. The Seven Gods' 8 attacks get new names 185-192.
- Debug Battle player sets: 309 = 7 Gods of Luck, 310-319 = Sea of Woods encounters, 320-324 and 326 = Nahash encounters, 325 = Nuckelavee.

## Leftover audit (test 26)
- Only items the game really gives were translated (the user said to skip placeholders). Gives were found by matching `push code, push n, push 0, callu f n=3` in the scripts (it finds the Ascetic Earrings and the Mr. Meiyuan card). Shop stock is in FIELD.BIN `shopTbl` (US 0x0060ea60, DC file 0x1b0560, 25 lists of {u8 kind, u8 index}).
- Accessory 34 is given by Carla in FI_00_U in both versions. Its record has 0 effects, so it became "Magnolia Charm" (no effect stated).
- Skipped, because nothing gives them or they are placeholders: ring items 47-50 Agility Down (no shop or script gives them in either version); accessories 28-33/35/36/40/48 and item 31 (placeholder names, no effects); key items 2, 7 (note), 74, 145 and 172-181; monsters with US name 54 and their attacks 3/32-52 (debug-map monsters only); Help (chunk 19) pages that the US left in Japanese.
- Beautiful Fool: FIELD.BIN, TAILOR.DAT, WI_13_U/PA_03_U, model 067, the CLOT record, name, note and explanation are identical in test 20 (earned in-game), v0.3 discs 1 and 2, and tests 25/26.

## Nelson's boat (test 27)
- The boat is not an event box. When CA_02_U loads, it calls `SetLookPoint(0, (-82.3, 21.7, -272.1), 15, event 4, 1, 1)`, but only if flag 4610 is set (by a scene in CA_03_U). EVENTBOX id 4 is a dead leftover: its flags 0x11 lack bit 2, which Cross needs, and `SetFieldData(1/2, ...)` never touches it.
- **Script rule:** the zero tail of a compiled script's code segment holds static variables (op 0x16 = code-segment address). Never strip it before appending code. `hook_ca02.py` used to, so it wrote the Nahash function over CA_02_U's window flag at 0x4940, and event 4 hung before its first message. `graft.py` keeps the full segment; every other patched script was audited and has its variables intact.
- Live test: `dcscene.py boat go` (flags 4610, 73 set, 42 clear; world-map point 18 must not be 2), then stand at the rowboat and press the action button.

## v0.3.1
- v0.3 plus tests 25-32: the monster attack names, the Magnolia Charm, the CA_02_U boat fix, battle help notes, skill-list titles, DC Help pages 128/129 and the Personal page titles. Built with `make_patch.py 0.3.1 ...` (see "Build inputs"). The manifest differs from v0.3 only in the five changed files.
- Verified: a patcher build of regular disc 1 matches DC test 32 in every file, and the other three discs differ from their v0.3 builds only in those five files.

## Build inputs (local only; never publish: they hold game data)
- `build/ovr`, `build/ovr2`: the override trees for discs 1 and 2 (disc paths, as passed to inject2.py; regular edition).
- `build/tailor_out/FIELD.BIN`: the patched root FIELD.BIN (both discs). `build/undub_out2/d1`, `d2`: undub.py output.
- `build/title_dc/`: the US `OPENING.DAT` (`OPENING_US.DAT`) plus each plated version (`OPENING_US_v03.DAT`, `OPENING_US_undub_v03.DAT`, ...).
- `x/`: extracted DC/US scripts (`dcmsc`, `usmsc`), `tailor_patches.json` (patch_tailor.py), survey logs. `tr/`: apply_text.py inputs.
- Rebuild the patch data from `tools/`:
  `python make_patch.py 0.3 ..\build\ovr ..\build\ovr2 ..\build\tailor_out\FIELD.BIN ..\build\undub_out2\d1 ..\build\undub_out2\d2 ..\build\title_dc\OPENING_US_undub_v03.DAT ..\release\patchdata.zip`

## v0.3
- v0.2 plus the Profile and Library fix above, and the plates `DIRECTORS_CUT_plate_v0.3.png` and `DIRECTORS_CUT_plate_undub_v0.3.png` (applied with `insert_plate.py` to the US `OPENING/OPENING.DAT`). Built with `make_patch.py 0.3 ...`. A patcher build of regular disc 1 matches the in-game-checked test 24 in every file except `OPENING/OPENING.DAT`.

## Title screen plate (test 22)
- `tools/insert_plate.py US_OPENING.DAT PLATE.png OUT.DAT` puts a "DIRECTOR'S CUT" plate (here `DIRECTORS_CUT_plate_jamie.png`, 384x48) under the US logo without any code change. It replaces opening.dat #4 (the rule line, drawn at (-12,173)) with a taller texture: the rule plus the plate, centred where the DC draws its own #21 plate (x centre 248, top y 181).
- Put the output in the overrides as `OPENING/OPENING.DAT` (both discs). `tools/menutex.py` decodes any opening.dat / menu texture bundle to PNGs.

## v0.2 builds
- Regular: test 23 plus the DC `OPENING/DEMO.LSD` (the opening movie, same name and different content in the DC) and the V0.2 plate (`DIRECTORS_CUT_plate_v0.2.png`). Both are applied with `tools/isopatch.py` (in place when the file fits, otherwise appended), and both are also in the override trees for full rebuilds.
- UnDub: `tools/undub.py DISC OUT` builds the Japanese-audio cutscenes, which `isopatch.py` writes into a copy of the regular build. The plate is `DIRECTORS_CUT_plate_undub_v0.2.png`. `..\UnDub\README.md` lists what was done to each cutscene.

## Release patcher (`release/`)
- `release/sh2dc_patcher.py` + `release/patchdata.zip` (+ `pcmscodec.exe`) rebuild either edition from the user's own four ISOs; usage is in `release/README.md`. The patch holds no game files: every changed file is a copy/add delta against files on the user's discs, and each source and result is checked by MD5.
- Regenerate the patch data after any change: `tools/make_patch.py VERSION OVR1 OVR2 FIELD.BIN UNDUB1 UNDUB2 UNDUB_OPENING.DAT release/patchdata.zip`. It encodes on every CPU thread in about a minute. Cutscenes use an aligned numpy block index (low memory), small files a 4-byte-step dictionary.
- The two 44.1 kHz UnDub scenes (N024, N104) are resampled and encoded on the user's machine (numpy + pcmscodec); only their subtitle times ship in the manifest.
- Placement: a replaced file goes over the old one when it fits. Otherwise the old space is freed, and new or moved files fill the freed gaps (largest first, best fit, the gap must lie after the file's directory base) before anything is appended. Before this, UnDub disc 2 was 15 MB over a DVD-5. Now the four discs are 3.92 / 4.64 / 3.96 / 4.65 GB (DVD-5 = 2,295,104 sectors).
- `tools/compare_iso.py A.iso B.iso US_ORIGINAL.iso DISC [OVERRIDE_DIR]` compares two builds file by file. The patcher's outputs match the reference builds for every file on both discs and both editions; N024 and N104 differ only by resampling noise (66–68 dB).

## Single disc (`--single-disc`)
- US disc 1 and disc 2 have byte-identical SLUS_210.41/.44 and identical non-LSD files; the LSD sets are disjoint (90 / 75). The disc number comes from the PVD volume set id ("0"/"1"), parsed by InitPkb(first) into g_disc_no (0x43fc70, gp-0x7d80).
- DiskChange(n) (0x3eea10) calls changeDiskNo (g_disc_no = n, diskState 0x43fc68 = 3). The IO thread (0x22aae0) handles state 3 (wait for a tray change, 0x216a28 == 1), then 2 (disc type), then 1 (InitPkb(0), which compares the PVD number with g_disc_no).
- Patches in SLUS_210.41: 0x2289d4 (skip the number compare), 0x22ab0c (skip the tray wait), 0x407604 (a save from the other disc adopts its number instead of prompting). DC_01_U.MSC ip 0x25b9: `push 2; callu 0x25c7` becomes `push 2; push 0; DiskChange n=2` (no DSKCHG screen).
- Script callers of DiskChange: only DC_01_U, plus the DB_00_U debug menu. Other g_disc_no readers: the Theater disc pages (FIELD.BIN 0x5542e8), save/load, and GameSection+0x64 (the saved disc).
- Verified in PCSX2: DC_01_U goes to OP_01_U, a disc 2 save loads after a reset, and Theater scenes play from both pages.
