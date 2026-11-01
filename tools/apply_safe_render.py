#!/usr/bin/env python3
"""Decouple R36S rendering from the native SMW simulation (release only).

Run after apply_overlay.py + apply_perf_overlay.py with R36S_RELEASE_BUILD=1.
The game advances at at most 60 fixed simulation ticks/s. Rendering may be
uncapped; no fake extra logic frames, skipped gameplay ticks or audio pitchups.
Unlike deleting the old frame delay, this does NOT speed up Mario.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: python3 tools/apply_safe_render.py REPO_ROOT")
root = Path(sys.argv[1]).resolve()
main = root / "src/main.c"
source = main.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global source
    n = source.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 exact anchor, found {n}")
    source = source.replace(old, new, 1)

replace_once(
    "  GamepadInfo *gi;\n\n  while (running) {",
    """  GamepadInfo *gi;

  // Fixed 60 Hz gameplay irrespective of display refresh or VSync.
  const Uint64 r36s_clock_hz = SDL_GetPerformanceFrequency();
  if (!r36s_clock_hz) Die("SDL high-resolution timer unavailable");
  const Uint64 r36s_logic_period = (r36s_clock_hz + 59u) / 60u;
  Uint64 r36s_next_logic_tick = SDL_GetPerformanceCounter();
  Uint64 r36s_last_render = 0;

  // 0 = unlimited rendering (default), otherwise optional user cap up to 360.
  // Use SMW_R36S_RENDER_MAX_FPS=60 on 60 Hz panels to avoid wasted GPU work.
  unsigned r36s_render_cap = 0;
  const char *r36s_cap_text = getenv("SMW_R36S_RENDER_MAX_FPS");
  if (r36s_cap_text && *r36s_cap_text) {
    char *end = NULL;
    long cap = strtol(r36s_cap_text, &end, 10);
    if (end && *end == 0 && cap >= 0 && cap <= 360)
      r36s_render_cap = (unsigned)cap;
  }
  const Uint64 r36s_render_period = r36s_render_cap ?
      (r36s_clock_hz + r36s_render_cap - 1) / r36s_render_cap : 0;

  while (running) {""",
    "timing-vars"
)

# Pausing should not build an enormous backlog of simulated frames.
replace_once(
    "    if (g_paused) {\n      SDL_Delay(16);\n      continue;\n    }",
    """    if (g_paused) {
      r36s_next_logic_tick = SDL_GetPerformanceCounter();
      SDL_Delay(16);
      continue;
    }""",
    "pause-clock"
)

first = "    // Clear gamepad inputs when joypad directional inputs to avoid wonkiness"
last = "    R36SFast_Pace(true);"
if source.count(first) != 1 or source.count(last) != 1:
    raise RuntimeError("expected the production overlays and 60 Hz pace call")
start = source.index(first)
end = source.index(last, start) + len(last)
loop_body = source[start:end]
draw = "    if (!g_snes->disableRender)\n      DrawPpuFrameWithPerf();\n"
if loop_body.count(draw) != 1:
    raise RuntimeError("unable to isolate single original drawing call")
loop_body = loop_body.replace(draw, "", 1).replace(last, "", 1)
# Logic, input, state recording, and audio queue are ticked ONLY at 60 Hz.
loop_body = "\n".join("  " + ln if ln.strip() else ln for ln in loop_body.split("\n"))
replacement = """    const Uint64 r36s_now = SDL_GetPerformanceCounter();
    if (r36s_now >= r36s_next_logic_tick) {
      // Drop missed scheduling slots instead of rushing frames to catch up.
      // This keeps gameplay at its native speed and avoids burst acceleration.
      if (r36s_now - r36s_next_logic_tick > r36s_logic_period)
        r36s_next_logic_tick = r36s_now;
      r36s_next_logic_tick += r36s_logic_period;
""" + loop_body + """
    }
    const Uint64 r36s_draw_now = SDL_GetPerformanceCounter();
    if (!g_snes->disableRender &&
        (!r36s_render_period ||
         !r36s_last_render ||
         r36s_draw_now - r36s_last_render >= r36s_render_period)) {
      // Re-presenting a 60 Hz game state does not invent new animation frames.
      // It is still useful for lower-latency screen updates on fast displays.
      DrawPpuFrameWithPerf();
      r36s_last_render = SDL_GetPerformanceCounter();
    } else {
      // Yield when rendering is capped or turbo skipped this frame.
      SDL_Delay(1);
    }"""
source = source[:start] + replacement + source[end:]
main.write_text(source, encoding="utf-8", newline="\n")
print("Safe R36S release: logic max 60 Hz, rendering independently paced.")
