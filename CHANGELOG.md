# Changelog: Shadow Hearts: Covenant, Director's Cut content port

This patch adds the content that was only in the Japanese *Shadow Hearts II Director's Cut* to the US *Shadow Hearts: Covenant* (both discs). It translates that content to English and reuses the official US script wherever a line already existed.

Ported by JamieTheAnything.

---

## v0.3.1 (`release/patchdata.zip`; the same as v0.3 except `COMMON/SSHMES.NA`, `COMMON/SSHDAT.NA`, `FIELD/MPS/CA_02_U.MSC`, `MENU/DAT/CMDMENU.MSD` and `MENU/MSD/PERSONAL.MSD`, on both discs and in both editions)

### Fixed

- **Nelson's boat in Cannes no longer freezes.** In v0.3, taking the boat to Sainte-Marguerite froze before "It's Nelson's boat." appeared, so Nahash could not be reached in normal play. The patched Cannes script had written the new Nahash code over one of the script's own variables (the "message window open" flag). The new code now goes after it, and the rest of the script is byte-identical to the US one. Verified in-game: the boat takes you into Nahash on the first crossing.

### Text and graphics

- **Monster attack names:** all 43 attacks used by the ten Director's Cut monsters showed "Unknown" in battle. 35 now use the official US names they share with other monsters (Slash, Surge, Rock Storm, Dark Claw, Magma, Gathering, Hail Crash, Bright Banish and others). The 7 Gods of Luck's eight attacks have new English names: Path to Yomi, Pure Integrity, Contentment, Great Majesty, Alms Giving, Charming Face, Divine Virtue and One Ailment.
- **Battle help notes:** the help line under several specials said "Unknown" (or "Unkown"). These now have notes in the US style: Veronica's Punish command, Heal, Hail Break and Stun Perfume; Lenny's Iron Claw; Nicolai's Divine Light.
- **Skill list titles:** Lenny's and Veronica's special-skill lists had a blank header. They now read "Iron Claw" and "Punish".
- **Page titles:** the top-left title image on Lenny's and Veronica's special-skill pages read "Soul Energy" and "Game Over" (the US left copies of those images in the two slots). They now read "Iron Claw" and "Punish", assembled from letters of the US title images so they match the other pages (`tools/personal_titles.py`).
- **Help pages for Iron Claw and Punish:** the two Director's Cut Help pages are added (Help > Special Abilities).
- **Carla's gift:** the accessory Carla gives in Florence for the Adriatic Magnolia showed "Unknown" (in the original US release too; the Director's Cut only has a developer placeholder). It is now "Magnolia Charm", with a note and an Explanation. The item has no effect in either version, and the text says so.

The title plate still reads V0.3.

---

## v0.3 (`release/patchdata.zip`; the same as v0.2 except `MENU/DAT/CMDMENU.MSD` and the title plate, on both discs and in both editions)

- **Title screen:** the plates now read "DIRECTOR'S CUT V0.3" and "DIRECTOR'S CUT UNDUB V0.3".
- **Profile:** Lenny and Veronica's Personal > Profile pages were still in Japanese. They now show "Lenny Curtis" and "Veronica Vera" with the official US Library text, which is the same text the Director's Cut uses for both pages.
- **Library:** the ten Director's Cut monsters now get Library entries once defeated, in the Director's Cut's order: Baphemetous, Luvar, Amphisbaena and Nuckelavee after #39, and Tsunemoto Bug, Hosojin, Itsumade, Futsutachi, Rasetsu and the 7 Gods of Luck before Solomon. The list now has 185 entries, numbered as in the Director's Cut. The US battle code was already recording these kills, but it had no Library records to show them, so saves where these fights are already won show the entries right away.

---

## v0.2 (build: `dc_patch_test\... [DC v0.2].iso`, both discs)

- **Opening movie:** the opening movie that plays before the title screen is now the Director's Cut one (`OPENING/DEMO.LSD`). The file has the same name in both versions, but the movie itself is different.
- **Title screen:** the plate now reads "DIRECTOR'S CUT V0.2 / PORTED BY: JAMIETHEANYTHING".
- **UnDub v0.2** (`UnDub\... [DC v0.2 UnDub].iso`): its plate reads "DIRECTOR'S CUT UNDUB V0.2". It already used the Director's Cut opening movie.
- **Patcher:** `release/sh2dc_patcher.py` builds either edition from your own US and Director's Cut ISOs. The patch contains no game files, only deltas and our own material, and it checks every file it reads and writes.
- **Single-disc version:** `--single-disc` builds one dual-layer image (6.9 GB) with both discs' content, and the game never asks for a disc swap. Tested: the end-of-disc-1 scene goes straight into disc 2, a disc 2 save loads, and Theater scenes play from both disc pages.
- **UnDub audio:** the Japanese tracks are now copied without re-encoding, trimmed or padded with up to 0.3 s of silence. Only N024 and N104, stored at 44.1 kHz in the Director's Cut, are resampled, on your own machine.

---

## v0.1 (build: DC test 23, both discs)

### New areas and story content

- **Nahash: the undersea temple** (`KS_00_U` … `KS_03_U`, `KS_10_U`)
  - It is reached from Sainte-Marguerite (`CA_02_U`). On the first boat crossing, the Director's Cut boat branch now plays.
  - All dialogue and on-screen captions are translated to English.
  - The Nuckelavee boss fight and the pact scene work.
- **Sea of Woods: the shrine dungeon** (`JU_00_U` … `JU_07_U`)
  - It is a new world-map point, unlocked by Shintaro's scene in `KT_03_U`. The world map shows "Sea of Woods" in its point list and banner.
  - The Seven Gods of Luck boss fight and its aftermath are in English.
- **Scenes added to existing maps.** These are spliced into the US scripts, so the US localisation of those maps is kept.
  - *Lucia & Veronica*: `MS_00_U` → `GT_04_U` → `GT_03_U`
  - *Anastasia's Fortune*: `FI_00_U`
  - *The Currymen*: `RE_03_U`
  - *Joachim in Japan*: new first-talk lines in `IN_00_U`
  - *Deeper into the Neam Ruins*: the `ND_04_A` exit now leads through the new floors `ND_11_U`–`ND_13_U` and `ND_10_U` to `ND_20_U`.
- **Mr. Meiyuan card and the Beautiful Fool** (`WI_13_U`)
  - Jimote's treasure-chest game gets the Director's Cut special round: 1000 Cash, with the Mr. Meiyuan card as the prize. It appears when the game detects a *Shadow Hearts* (1) save on the memory card.
  - Pierre in Paris (`PA_03_U`) then trades the card for Cornelia's new dress.

### Disc 2

- **N125 "The Promise"** now uses the Director's Cut pre-rendered movie instead of the in-engine scene.
  - English dub audio (fan-supplied), synced to the movie.
  - English subtitles, taken from the official US script and retimed to the dub.

### New costume: Beautiful Fool (Cornelia)

- New dress 11 in Gepetto's **Change Dress** list. The US list was capped at 10, and the cap is raised to 11.
- Includes its name, the note "Cornelia's dress. Non-class. Lowers all attacks.", the Explanation text, and the Director's Cut sketch-book page and model.

### Items

| Item | Type | Added |
|---|---|---|
| Azure Orb | Item | Note "An orb that glows a pale blue." and Explanation text. The US version had none. |
| Ascetic Earrings | Accessory | Name, note "Soul Energy gained increases 20%." and Explanation. It's a prize in the `WI_12_U`/`WI_13_U` minigames and showed as "Unknown" before. |
| Noble Thief Soul | Key item | Name, note and Explanation (Louis Mandrin's tools). No in-game source has been found. |
| Mr. Meiyuan | Key item | Now obtainable (see the Meiyuan card entry above). |

### Text and data fixes

- **Rene → Lenny** in the party-member and preset name data, matching the US dialogue.
- **Iron Clow → Iron Claw**, and **Panish → Punish**, everywhere they appear: battle, menus and the Personal screen.
- **Veronica's skills** now show their names: Heal, Hail Break and Stun Perfume. In the US data all three pointed at "Unknown".
- The Personal screen's technique labels for Lenny and Veronica are in English.
- Japanese wavy dashes in the new scenes' dialogue are written as `...` instead of `~`. The US font draws `~` as an apostrophe.

### Title screen

- A "DIRECTOR'S CUT V0.1 / PORTED BY: JAMIETHEANYTHING" plate sits under the logo, in the spot where the Director's Cut draws its own plate. No game code changes.

### Engine and technical notes

- DC-only files are appended to the end of each disc image. `PKFINFO.TBL` is extended, and existing US files are repointed to patched copies. Original files are not moved.
- `FIELD.BIN` is patched in place so the tailor and Change Dress code handle 11 dresses. Its size is unchanged, and it is identical on both discs.
- `SHOP/TAILOR.DAT` gains the Beautiful Fool sketch-book page and its Change Dress explanation.
- Script grafting follows the VM's rule: a detour only rejoins the US code on a statement boundary. This fixed a crash when talking to Joachim twice.

---

### UnDub edition (separate build, `UnDub\` folder)

- Same as v0.1, but every cutscene uses the Japanese voice track from the Director's Cut: 90 on disc 1, 75 on disc 2.
- English subtitles are kept and shown at the Japanese lines' timing.
- The opening movie is the Director's Cut opening.
- Five scenes the US re-cut noticeably for the English dub use the whole Director's Cut cutscene, with the English subtitles grafted in: N060, N010, M15, the good ending, and N125 "The Promise". Three more with small re-cuts (G04B, N100B, N128) also use the Director's Cut file.
- A few scenes drift by up to about 1 second, because the US subtitle font was too big to graft into the Director's Cut file. `UnDub\README.md` lists what was done to each cutscene.

---

## Verified in-game (PCSX2)

| Content | Build |
|---|---|
| Nahash intro, Nuckelavee fight, pact scene | test 5 |
| Sea of Woods (hub, shrine, boss, aftermath, Shintaro) and world map name | test 9 |
| N125 movie, dub audio, English subtitles | test 12 (disc 2) |
| Anastasia's Fortune, Currymen | test 13 / 14 |
| Lucia & Veronica, Joachim (talked to repeatedly), Neam `ND_04_A` → `ND_11_U` | test 14 |
| Azure Orb note and Explanation | test 15 / 16 |
| Ascetic Earrings, Noble Thief Soul | test 17 |
| Beautiful Fool in Change Dress, wearable | test 19 |
| Beautiful Fool explanation and sketch page | test 20 |
| Meiyuan card won in the 1000-Cash round; Pierre gives the dress | test 20 |
| Title plate | test 22 (first plate); test 23 not yet checked |

## Known issues and not done yet

- **Shadow Hearts 1 save check:** not tested with a real save. The 1000-Cash round was tested by setting the "save found" value by hand. The US game still scans for the US *Shadow Hearts* save, `BASLUS-20347`, on the title screen, and stores the result when you start a New Game.
- **Nahash boat trigger:** not tested in normal play, only by forcing the event. The story flag that opens the boat menu is unknown.
- **Neam Ruins:** the full walk from `ND_12_U` to `ND_10_U` to `ND_20_U` has not been played, and neither have the Nahash floors `KS_01_U`–`KS_03_U`.
- **Old saves:** saves made before the patch keep "Rene" as the party member's name. The name is stored when the character joins.
- **Still untranslated:** skill descriptions, the extra Director's Cut library entries (monsters and people), and ring items 47–50 (skipped).
- **Tailor shop:** not re-checked after the 11-dress change. Change Dress is verified.
- **Not ported:** Director's Cut debug-only variant maps (`_D`, `_9`, `_QUIZ` copies, `MS_2x`–`5x`, `HE_15`–`24`). Nothing in normal play reaches them. The Ring Soul quizzes are already in the US release.
