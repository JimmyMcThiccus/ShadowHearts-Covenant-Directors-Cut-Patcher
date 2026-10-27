# Shadow Hearts: Covenant: Director's Cut content port (v0.3.2)

This patcher builds a copy of the US *Shadow Hearts: Covenant* with the content that was only in the Japanese *Shadow Hearts II Director's Cut*, translated into English. See `CHANGELOG.md` for the full list.

Ported by JamieTheAnything.

There are two editions:

- **regular**: English, with the Director's Cut content added and the Director's Cut opening movie.
- **undub**: the same, but with the Japanese voices from the Director's Cut: every cutscene, every battle (party members and monsters) and the in-engine story scenes on the map. The English subtitles stay on.

## What you need

- Your own disc images (ISO) of:
  - *Shadow Hearts: Covenant* (USA), discs 1 and 2
  - *Shadow Hearts II Director's Cut* (Japan), discs 1 and 2
- Python 3.8 or newer.
- For the **undub** edition only: `numpy` (`pip install numpy`). `scipy` is optional and gives slightly better resampling. Two cutscenes have Japanese audio stored at a different sample rate, so the patcher converts them with the bundled `pcmscodec.exe`. Without numpy, those two scenes keep their English audio and the rest of the build is unaffected.

The patch contains no game files. It rebuilds everything from your discs and checks each one, so a bad or different dump is reported instead of producing a broken game.

## How to use it

Keep `sh2dc_patcher.py`, `patchdata.zip` and `pcmscodec.exe` in the same folder, then run:

```bash
python sh2dc_patcher.py --edition regular --us1 "US Disc 1.iso" --us2 "US Disc 2.iso" --dc1 "DC Disc 1.iso" --dc2 "DC Disc 2.iso" --out "Patched"
```

For the UnDub edition, change `--edition regular` to `--edition undub`. To build one disc only, add `--discs 1` (disc 1 needs only `--us1` and `--dc1`).

The patcher uses every CPU thread your computer has. Each disc takes from a few seconds to a minute (most of it copying the ISO) and needs about 5 GB of free space. Your original ISOs are never changed. The patched discs are written to the `--out` folder:

- `Shadow Hearts - Covenant (USA) (Disc 1) [DC v0.3.2].iso`
- `Shadow Hearts - Covenant (USA) (Disc 1) [DC v0.3.2 UnDub].iso`

## Single-disc version (no disc swapping)

Add `--single-disc` to build one image that holds both discs' content. The game never asks you to change discs. All four ISOs are needed:

```bash
python sh2dc_patcher.py --edition regular --single-disc --us1 "US Disc 1.iso" --us2 "US Disc 2.iso" --dc1 "DC Disc 1.iso" --dc2 "DC Disc 2.iso" --out "Patched"
```

This writes `Shadow Hearts - Covenant (USA) [DC v0.3.2 Single Disc].iso` (6.9 GB), or `[DC v0.3.2 UnDub Single Disc]` with `--edition undub`. It is too big for a single-layer DVD. It runs in PCSX2 or from OPL (on the internal HDD, a network share, or an exFAT USB drive with a recent OPL), or it can be burned to a dual-layer DVD.

How it works: the two US discs run the same program and differ only in their cutscenes, so disc 2's 75 cutscenes are added to disc 1. Four small patches then make every disc change succeed immediately:
- the game no longer compares the disc number in the disc header;
- it no longer waits for the drive tray to open and close;
- loading a disc 2 save simply switches to disc 2;
- the end-of-disc-1 scene changes disc without showing the "insert disc 2" screen.

The game still tracks which disc the story is on, so saves and the Theater's disc pages work as normal. Saves are compatible with the two-disc version.

## Notes

- Saves from the unpatched US game work. Party members who joined before patching keep the name they were saved with ("Rene" rather than "Lenny").
- Every two-disc build fits a single-layer DVD (DVD-5, the PS2's single-layer limit). The largest, UnDub disc 2, is 4.66 GB. The patcher prints the size and whether it fits after each disc.
- The audio codec's source is in `pcmscodec_src` (Rust). On Linux or macOS, build it with `cargo build --release` and put the `pcmscodec` binary next to the script.

## Repository layout

To patch your discs you only need the four files at the top: `sh2dc_patcher.py`, `patchdata.zip`, `pcmscodec.exe` and this README. Everything else is the toolchain used to make the patch.

- `pcmscodec_src/`: source for `pcmscodec.exe`, the PS2 audio (SPU-ADPCM) codec (Rust).
- `tools/`: the Python scripts that extract, translate, graft and repack the Director's Cut content. `tools/make_patch.py` builds `patchdata.zip` from finished builds.
- `translations/`: the English text for the new areas and scenes.
- `plates/`: the title-screen plates for each version.
- `msccalls/`: a small Rust helper that lists script engine calls.
- `docs/DEVELOPMENT.md`: format notes and build steps.
