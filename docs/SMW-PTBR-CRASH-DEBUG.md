# SMW R36S — PT-BR Crash Debug (Vanilla Dome 1 intact)

This build is designed to reproduce the stage-entry crash reported after
installing a translated `smw_assets.dat`. It is a **diagnostic build**,
not a translation rewrite or an attempted bug fix.

The gameplay code is identical to
`feature/ptbr-visual-sem-nintendo`, with only read-only trace
statements added to stage loading. The old speculative pipe recovery is
**disabled** in the dedicated launcher; the stock secondary entrance tables
are expected in the user's own corrected `smw_assets.dat`.

## Installation

1. Back up your working R36S `smw-r36s` installation.
2. From the ZIP, copy the two binaries (`smw` and `smw-gles2`) into the
   same directory where `smw_assets.dat` and `smw.ini` currently reside.
3. Copy `SMW-R36S-PTBR-Debug.sh` beside the existing PortMaster launcher
   (or into the executable directory if there is no nested `smw-r36s/`).
4. **DO NOT replace or edit the `smw_assets.dat` that crashed**.
   The exact same file is vital for reproduction.
5. Keep `saves/`, your existing `smw.ini`, and `background.png`.
6. Run `SMW-R36S-PTBR-Debug.sh` from Ports.
7. Enter the same stage that crashed previously. If you are kicked back
   to the Ports menu, collect the logs from the game's `logs/` folder.

## Files to send back

- `logs/ptbr-run-YYYYMMDD-HHMMSS.log` — shell output and asset SHA-256.
- `logs/r36s-diagnostic.log` — game's signal handler, state/level trace,
  `PTBR_LEVEL_LOAD_BEGIN`, `LEVEL_ASSET`, `PTBR_LEVEL_DATA`,
  `PTBR_SPRITE_HEADER`, `PTBR_LEVEL_LOAD_DONE`,
  `FATAL_SIGNAL` with program counter (when catchable).
- Say which **level** caused the crash, and whether it occurred on a
  message box, stage load, sublevel/pipe or normal gameplay.

The older `r36s-diagnostic.log` is preserved as
`logs/r36s-diagnostic-prev-<timestamp>.log` on new run.

## Known translation fingerprints

The launcher prints SHA-256 so a crash from different asset versions
cannot be conflated:

| Assets file | SHA256 (first 16 hex digits) |
|---|---|
| User's original corrected DAT | `86274eb42561664d` |
| First PT-BR messages-only translation | `c1f4bf341c4f8116` |
| Intermediate expanded translation | `1e9e93aabd8e1938` |
| Latest expanded PT-BR translation | `2279d49f22c1c5cd` |

These hashes are fingerprints, not proof of translation correctness.
All these files keep the original length of 880,156 bytes, but a
same-length text edit can still corrupt control bytes and provoke crashes.
The debug build only identifies the failure; it does not automatically
make a broken DAT safe.

Debug symbols (`debug-symbols/*.debug`) are included for later
`addr2line` / GDB symbolization of a logged `pc`; keep the original
matching .debug file from the same ZIP. To compare reliably, use the
**same** savegame and **same** translated DAT throughout the test.

The ZIP does not redistribute ROMs or commercial extracted asset data.
