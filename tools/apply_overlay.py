#!/usr/bin/env python3
"""Apply R36S tracing to upstream sources inside the GitHub Actions workspace.

The repo's Windows/Linux desktop source remains untouched in git.
Run: python3 tools/apply_overlay.py .
"""
from pathlib import Path
import shutil
import sys

BASE = Path(__file__).resolve().parent.parent
if len(sys.argv) != 2:
    sys.exit("Usage: python3 tools/apply_overlay.py /path/to/smw")
repo = Path(sys.argv[1]).resolve()
main = repo / "src/main.c"
if not (repo / "Makefile").exists() or not main.exists():
    sys.exit("ERROR: target is not snesrev/smw source tree")
source = main.read_text(encoding="utf-8")
if '"r36s_diag.h"' in source:
    sys.exit("ERROR: diagnostics already applied; no changes made")

changes = [
    ('#include "smw_spc_player.h"', '#include "smw_spc_player.h"\n#include "r36s_diag.h"'),
    ('void NORETURN Die(const char *error) {\n',
     'void NORETURN Die(const char *error) {\n  R36SDiag_Message("DIE", error);\n'),
    ('  ParseConfigFile(config_file);\n\n  LoadAssets();',
     '  R36SDiag_Init();\n  R36SDiag_Message("PHASE", "Parsing configuration");\n'
     '  ParseConfigFile(config_file);\n\n'
     '  R36SDiag_Message("PHASE", "Loading asset table");\n'
     '  LoadAssets();\n  R36SDiag_Message("PHASE", "Assets loaded");'),
    ('  Snes *snes = SnesInit(kRom, kRom_SIZE);',
     '  R36SDiag_Message("PHASE", kRom_SIZE ? "Starting with ROM comparison" : '
     '"Starting WITHOUT ROM comparison");\n'
     '  Snes *snes = SnesInit(kRom, kRom_SIZE);'),
    ('    uint8 is_replay = RtlRunFrame(inputs | GetActiveControllers());\n\n    frameCtr++;',
     '    R36SDiag_BeforeFrame(frameCtr + 1, inputs);\n'
     '    uint8 is_replay = RtlRunFrame(inputs | GetActiveControllers());\n\n'
     '    frameCtr++;\n'
     '    R36SDiag_AfterFrame(frameCtr, inputs, g_got_mismatch_count, game_id);'),
    ('    if (g_paused != audiopaused) {',
     '    /* Hold SELECT/BACK + START for 2 seconds to exit, even if paused. */\n'
     '    {\n'
     '      static uint32 quit_held_since = 0;\n'
     '      uint32 mask = (1u << kGamepadBtn_Back) | (1u << kGamepadBtn_Start);\n'
     '      int held = (g_gamepad[0].modifiers & mask) == mask;\n'
     '      if (!held) quit_held_since = 0;\n'
     '      else if (!quit_held_since) quit_held_since = SDL_GetTicks();\n'
     '      else if ((uint32)(SDL_GetTicks() - quit_held_since) >= 2000) {\n'
     '        R36SDiag_Message("INPUT", "SELECT+START held 2 seconds: exiting");\n'
     '        running = false;\n'
     '        break;\n'
     '      }\n'
     '    }\n'
     '    if (g_paused != audiopaused) {'),
    ('  SDL_DestroyWindow(window);\n  SDL_Quit();\n  return 0;',
     '  SDL_DestroyWindow(window);\n  SDL_Quit();\n  R36SDiag_Close();\n  return 0;'),
    ('    printf("Failed to lock texture: %s\\n", SDL_GetError());\n    return;',
     '    R36SDiag_Message("SDL_ERROR", SDL_GetError());\n    Die("Unable to lock SDL texture");'),
    ('  if (!VerifyAssetsFile(data, length))\n'
     '    Die("Mismatching assets file - Please re run \'python assets/restool.py\'");',
     '  if (!VerifyAssetsFile(data, length))\n'
     '    Die("Mismatching assets file - Please re run \'python assets/restool.py\'");\n'
     '  R36SDiag_Assets(length, kNumberOfAssets);'),
]

for old, new in changes:
    count = source.count(old)
    if count != 1:
        sys.exit(f"ERROR: upstream anchor count {count}, expected 1: {old[:100]!r}; NOT MODIFIED")
    source = source.replace(old, new, 1)

for name in ("r36s_diag.c", "r36s_diag.h"):
    src = BASE / "overlay/src" / name
    if not src.is_file():
        sys.exit(f"ERROR: overlay file not found: {src}")
if (repo / "src/main.c.before-r36s-debug").exists():
    sys.exit("ERROR: previous backup detected")

shutil.copy2(main, repo / "src/main.c.before-r36s-debug")
main.write_text(source, encoding="utf-8", newline="\n")
for name in ("r36s_diag.c", "r36s_diag.h"):
    shutil.copy2(BASE / "overlay/src" / name, repo / "src" / name)

print("R36S instrumentation applied to build workspace (not tracked in git)")
