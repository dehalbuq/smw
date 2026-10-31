# SMW R36S — Production release (Cortex-A35, capped 60 FPS)

**Branch:** `release/r36s-cortex-a35-60fps`, separate from
`feature/r36s-performance-43-pixelperfect` and `main`.

**Build:** [GitHub Actions run 41218076961](https://github.com/dehalbuq/smw/actions/runs/41218076961).
CI passed ARM64 cross/native build and verified both executables are
AArch64, fully stripped, free of `.debug_*` and `.symtab` sections.

## Performance changes

- GCC `-O3 -g0 -DNDEBUG -DR36S_RELEASE -flto=auto -mcpu=cortex-a35 -mtune=cortex-a35`.
  The port preserves `-fwrapv -fno-strict-aliasing` to avoid breaking
  SNES arithmetic/translations and does **not** use risky `-ffast-math`.
- Native-only engine `RM_MINE`, not a second emulated comparison engine.
- Diagnostic file writes, signal hooks and per-frame telemetry removed at
  compile time; runtime launcher does not redirect output to logs.
- GLES2 direct BGRA upload of the SNES ARGB8888 buffer when
  `GL_EXT_texture_format_BGRA8888` is supported; safe fallback to
  RGBA conversion and upload if absent or rejected.
- Frame cap: monotonic SDL counter, minimum `ceil(freq/60)` ticks
  between simulated frames; does not catch up by running frames faster
  after a slow frame. Driver VSync remains enabled by default.
  This is a **limit**, not a guarantee of achieving 60 FPS.
- Original 4:3 pixel-perfect content, decorative background, SELECT+START
  exit UI, 32 kHz audio and 1024-sample buffer preserved.

## Installation

Place `smw`, `smw-gles2`, `smw.ini` and `background.png` beside
the existing **corrected** `smw_assets.dat` under
`/roms/ports/smw-r36s/` (or the nested `smw-r36s/` used by the
launcher). Keep `saves/`. Run `SMW-R36S.sh` instead of
`SMW-R36S-Debug.sh`.

The built artifact does not include ROM or proprietary extracted assets,
and the GitHub Actions artifact does not embed the generated
`background.png`. The assembled ZIP provided to the user does.

The confirmed fix for Vanilla Dome 1 was to restore the missing bank-05
secondary entrance tables within `smw_assets.dat`; **never** replace
that fixed file with an older asset file.

## Caveats and measurements

User's last v5 test: approximately 58.39 FPS on average, 58.5 maximum
in logged 600-frame samples, VSync enabled, no ALSA underruns.
Whether this production build reaches closer to 60 depends on hardware
refresh, Mali/EGL display stack, thermal/power management and workload.
CI confirms compilation and binary integrity, not R36S hardware FPS.
