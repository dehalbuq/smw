# SMW Recomp experimental — R36S

**Not an official PortMaster catalog release.** Experimental independent port
of the Matthew Stanley SNES static recompilation project. Unlike the existing
snesrev-based SMW release, this one uses the mstan/SuperMarioWorldRecomp engine
and its optional runtime mods. No copyrighted ROM distributed.

## Install by hand
1. Extract the artifact archive. It contains the top-level folder
   `smwrecompr36s/`, itself containing a launcher `SMW Recomp R36S.sh`,
   `port.json` and the inner `smwrecompr36s/` directory.
2. Copy the launcher and inner game directory to your SD's ROMs/ports directory
   (e.g. `/roms/ports/` or `/roms2/ports/`). Avoid nesting the root
   `smwrecompr36s` wrapper an extra level.
3. Place your own legally obtained USA ROM at
   `/roms/ports/smwrecompr36s/smw.sfc`.
4. Set executable permission on the binary and launcher if your SD filesystem
   retains Unix permissions, or use a Linux file manager/SSH to run chmod +x.
5. Launch `SMW Recomp R36S` from the Ports menu.

## Defaults
- R36S LCD: 640x480, 4:3, OpenGL ES2, SDL2, no linear filtering.
- Gamepad support enabled, games use firmware's native control mappings.
- If PortMaster is installed and `GPTOKEYB` is set, its normal hotkey+Start
  force quit is enabled (typically Select+Start on the R36S).
- Adaptive widescreen and native co-op manifests are preserved, but on the
  R36S LCD start with 4:3. More demanding mods remain experimental.
- Asset helper for Captain Falcon and ICE online network support are disabled
  for this initial ARM64 build. Their manifest presence is not proof of
  functional compatibility.

## Diagnostics
`smwrecompr36s/smw-r36s.log` records startup and exit. A separate
`smwrecompr36s/diagnose_r36s.sh` collects ABI/loader info. Run it if the
game does not open, then share its output and your firmware name/version.

## Compatibility note
PortMaster's R36S ArkOS entry identifies glibc 2.30. This build targets
Debian Buster glibc 2.28 and should not require newer GLIBC symbols.
**A successful build is not hardware qualification.** SDL2, EGL/GLES driver,
controller mapping, fullscreen presentation, memory use and speed require
testing on dArkOSRE and ArkOS4Clone. Do not replace firmware system libraries.

Upstream: https://github.com/mstan/SuperMarioWorldRecomp
PortMaster documentation: https://portmaster.games/contribute/porting/packaging/
