#!/usr/bin/env python3
"""Regression: SDLActivity may run SDL_main repeatedly in the same Android process."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
CC = shutil.which("cc") or shutil.which("gcc")
if not CC:
    raise RuntimeError("A C compiler is required for menu lifecycle regression checks")

STUB_SDL = """#ifndef SDL_H_STUB
#define SDL_H_STUB
#include <stdint.h>
typedef uint32_t Uint32;
Uint32 SDL_GetTicks(void);
#endif
"""
HARNESS = r"""
#include <assert.h>
#include <stdint.h>
#include "android_quit_menu.h"

static uint32_t ticks = 0;
uint32_t SDL_GetTicks(void) { return ticks; }

static void press(bool sel, bool start, bool a, bool b) {
  AndroidQuitMenu_Poll(sel, start, a, b);
  ticks += 16;
}

int main(void) {
  /* First launch: chord -> release -> A confirms exit */
  AndroidQuitMenu_Reset();
  assert(!AndroidQuitMenu_IsOpen() && !AndroidQuitMenu_WantsExit());
  press(true, true, false, false);
  assert(AndroidQuitMenu_IsOpen() && !AndroidQuitMenu_WantsExit());
  press(false, false, false, false);
  press(false, false, true, false);
  assert(AndroidQuitMenu_WantsExit());

  /* Second launch, same shared library: the previous exit MUST be forgotten */
  AndroidQuitMenu_Reset();
  assert(!AndroidQuitMenu_IsOpen() && !AndroidQuitMenu_WantsExit());
  press(false, true, false, false);
  assert(!AndroidQuitMenu_IsOpen() && !AndroidQuitMenu_WantsExit());
  press(false, false, false, false);
  press(true, true, false, false);
  assert(AndroidQuitMenu_IsOpen() && !AndroidQuitMenu_WantsExit());
  press(false, false, false, false);
  press(false, false, false, true);
  assert(!AndroidQuitMenu_IsOpen() && !AndroidQuitMenu_WantsExit());

  /* Third launch: exit only after a new confirmation, never automatically */
  AndroidQuitMenu_Reset();
  for (int i=0; i<20; i++) press(false, false, false, false);
  assert(!AndroidQuitMenu_WantsExit());
  press(true, true, false, false);
  press(false, false, false, false);
  press(false, true, false, false);
  assert(AndroidQuitMenu_WantsExit());
  return 0;
}
"""

with tempfile.TemporaryDirectory(prefix="smw-menu-lifecycle-") as td:
    folder = Path(td)
    (folder / "SDL.h").write_text(STUB_SDL)
    (folder / "test.c").write_text(HARNESS)
    command = [
        CC, "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-I", str(folder), "-I", str(ROOT),
        str(ROOT / "android_quit_menu.c"), str(folder / "test.c"),
        "-o", str(folder / "test"),
    ]
    subprocess.run(command, check=True)
    subprocess.run([str(folder / "test")], check=True)
print("OK: exit, cancel, and repeated SDL_main relaunch do not retain quit latch")
