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
    ('#include "smw_spc_player.h"', '#include "smw_spc_player.h"\n#include "r36s_diag.h"\n#include "r36s_quit_menu.h"\n#include "r36s_video.h"\n#include "r36s_gles2.h"'),
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
    # GameController mappings on some RK3326 firmwares omit physical
    # Select/Start. SDL joystick button 12/13 is the documented R36S layout;
    # expose overrides for clone boards and log raw IDs to confirm.
    ('  for (int i = 0; i < SDL_NumJoysticks(); i++)\n    OpenOneGamepad(i);',
     '  SDL_JoystickEventState(SDL_ENABLE);\n'
     '  R36SDiag_Message("INPUT", "Raw joystick SELECT/START fallback enabled; '
     'defaults b12/b13; configurable via SMW_R36S_SELECT_BUTTON/SMW_R36S_START_BUTTON");\n'
     '  for (int i = 0; i < SDL_NumJoysticks(); i++)\n    OpenOneGamepad(i);'),
    ('      case SDL_MOUSEWHEEL:',
     '      case SDL_JOYBUTTONDOWN:\n'
     '      case SDL_JOYBUTTONUP: {\n'
     '        gi = GetGamepadInfo(event.jbutton.which);\n'
     '        static unsigned raw_log_count = 0;\n'
     '        if (raw_log_count++ < 64) {\n'
     '          char msg[160];\n'
     '          snprintf(msg, sizeof(msg), "joystick=%d raw_button=%u pressed=%d recognized=%d",\n'
     '                   (int)event.jbutton.which, (unsigned)event.jbutton.button,\n'
     '                   event.type == SDL_JOYBUTTONDOWN, gi != NULL);\n'
     '          R36SDiag_Message("RAW_JOY", msg);\n'
     '        }\n'
     '        const char *sel_env = getenv("SMW_R36S_SELECT_BUTTON");\n'
     '        const char *start_env = getenv("SMW_R36S_START_BUTTON");\n'
     '        int sel = sel_env ? atoi(sel_env) : 12;\n'
     '        int start = start_env ? atoi(start_env) : 13;\n'
     '        int mapped = event.jbutton.button == sel ? kGamepadBtn_Back :\n'
     '                     event.jbutton.button == start ? kGamepadBtn_Start : -1;\n'
     '        if (gi && mapped >= 0) {\n'
     '          HandleGamepadInput(gi, mapped, event.type == SDL_JOYBUTTONDOWN);\n'
     '          char msg[128];\n'
     '          snprintf(msg, sizeof(msg), "raw=%d mapped=%s pressed=%d",\n'
     '                   (int)event.jbutton.button, mapped == kGamepadBtn_Back ? "SELECT" : "START",\n'
     '                   event.type == SDL_JOYBUTTONDOWN);\n'
     '          R36SDiag_Message("MENU_BUTTON", msg);\n'
     '        }\n'
     '        break;\n'
     '      }\n'
     '      case SDL_MOUSEWHEEL:'),
    ('          if (b >= 0)\n            HandleGamepadInput(gi, b, event.type == SDL_CONTROLLERBUTTONDOWN);',
     '          if (b >= 0) {\n'
     '            HandleGamepadInput(gi, b, event.type == SDL_CONTROLLERBUTTONDOWN);\n'
     '            if (b == kGamepadBtn_Back || b == kGamepadBtn_Start || b == kGamepadBtn_Guide) {\n'
     '              char msg[120];\n'
     '              snprintf(msg, sizeof(msg), "SDL_Controller raw=%u mapped=%d pressed=%d",\n'
     '                       (unsigned)event.cbutton.button, b, event.type == SDL_CONTROLLERBUTTONDOWN);\n'
     '              R36SDiag_Message("MENU_BUTTON", msg);\n'
     '            }\n'
     '          }'),
    ('    printf("Found controller \'%s\' assigning to player %d\\n", SDL_GameControllerName(controller), found_idx + 1);',
     '    printf("Found controller \'%s\' assigning to player %d\\n", SDL_GameControllerName(controller), found_idx + 1);\n'
     '    {\n'
     '      char *mapping = SDL_GameControllerMapping(controller);\n'
     '      R36SDiag_Message("CONTROLLER_MAPPING", mapping ? mapping : "SDL mapping unavailable");\n'
     '      if (mapping) SDL_free(mapping);\n'
     '    }'),
    ('  g_renderer_funcs.EndDraw();',
     '  R36SQuitMenu_Draw(pixel_buffer, pitch, g_snes_width * render_scale,\n'
     '                    g_snes_height * render_scale, render_scale);\n'
     '  g_renderer_funcs.EndDraw();'),
    ('    while (SDL_PollEvent(&event)) {\n      switch (event.type) {',
     '    while (SDL_PollEvent(&event)) {\n'
     '      if (R36SQuitMenu_HandleEvent(&event)) continue;\n'
     '      switch (event.type) {'),
    ('  SDL_RenderClear(g_renderer);\n  SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, NULL);',
     '  SDL_RenderClear(g_renderer);\n'
     '  if (r36s_viewport_16_9) {\n'
     '    int w = 0, h = 0;\n'
     '    SDL_GetRendererOutputSize(g_renderer, &w, &h);\n'
     '    R36SViewport r; R36SVideo_ContentRect(w, h, &r);\n'
     '    SDL_Rect rect = { r.x, r.y, r.w, r.h };\n'
     '    SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, &rect);\n'
     '  } else SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, NULL);'),
    ('  if (g_config.output_method == kOutputMethod_OpenGL) {\n'
     '    g_win_flags |= SDL_WINDOW_OPENGL;\n'
     '    OpenGLRenderer_Create(&g_renderer_funcs);\n'
     '  } else {',
     '  if (g_config.output_method == kOutputMethod_OpenGL) {\n'
     '    g_win_flags |= SDL_WINDOW_OPENGL;\n'
     '    OpenGLRenderer_Create(&g_renderer_funcs);\n'
     '  }\n'
     '#ifdef R36S_GLES2_SUPPORT\n'
     '  else if (g_config.output_method == kOutputMethod_R36S_GLES2) {\n'
     '    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);\n'
     '    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);\n'
     '    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);\n'
     '    g_win_flags |= SDL_WINDOW_OPENGL;\n'
     '    R36SGLES2Renderer_Create(&g_renderer_funcs);\n'
     '  }\n'
     '#endif\n'
     '  else {'),
    ('    if (g_paused != audiopaused) {',
     '    R36SQuitMenu_Update();\n'
     '    if (R36SQuitMenu_WantsExit()) {\n'
     '      running = false;\n'
     '      break;\n'
     '    }\n'
     '    if (R36SQuitMenu_IsOpen()) {\n'
     '      if (g_audio_device) SDL_PauseAudioDevice(g_audio_device, 1);\n'
     '      audiopaused = true;\n'
     '      DrawPpuFrameWithPerf();\n'
     '      SDL_Delay(16);\n'
     '      continue;\n'
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

for name in ("r36s_diag.c", "r36s_diag.h", "r36s_quit_menu.c", "r36s_quit_menu.h", "r36s_video.c", "r36s_video.h", "r36s_gles2.c", "r36s_gles2.h"):
    src = BASE / "overlay/src" / name
    if not src.is_file():
        sys.exit(f"ERROR: overlay file not found: {src}")
if (repo / "src/main.c.before-r36s-debug").exists():
    sys.exit("ERROR: previous backup detected")

shutil.copy2(main, repo / "src/main.c.before-r36s-debug")
main.write_text(source, encoding="utf-8", newline="\n")
for name in ("r36s_diag.c", "r36s_diag.h", "r36s_quit_menu.c", "r36s_quit_menu.h", "r36s_video.c", "r36s_video.h", "r36s_gles2.c", "r36s_gles2.h"):
    shutil.copy2(BASE / "overlay/src" / name, repo / "src" / name)

# Add the experimental renderer selection only to the transient build workspace.
# Unmodified upstream file remains on main; this does not touch gameplay code.
config_h = repo / "src/config.h"
config_c = repo / "src/config.c"
h = config_h.read_text(encoding="utf-8")
c = config_c.read_text(encoding="utf-8")
h_anchor = '  kOutputMethod_OpenGL,'
if h.count(h_anchor) != 1:
    sys.exit("ERROR: config.h OpenGL enum anchor not found")
h = h.replace(h_anchor, h_anchor + '\\n  kOutputMethod_R36S_GLES2,', 1)
c_includes = '#include "config.h"'
if c.count(c_includes) != 1:
    sys.exit("ERROR: config.c include anchor not found")
c = c.replace(c_includes, c_includes + '\\n#include "r36s_video.h"', 1)
c_anchor = '    } else if (StringEqualsNoCase(key, "IgnoreAspectRatio")) {'
if c.count(c_anchor) != 1:
    sys.exit("ERROR: config.c viewport anchor not found")
c = c.replace(c_anchor,
    '    } else if (StringEqualsNoCase(key, "ViewportMode")) {\\n'
    '      return R36SVideo_ParseViewport(value);\\n' + c_anchor, 1)
c_output = 'StringEqualsNoCase(value, "OpenGL") ? kOutputMethod_OpenGL : kOutputMethod_SDL;'
if c.count(c_output) != 1:
    sys.exit("ERROR: config.c output selector anchor not found")
c = c.replace(c_output,
    'StringEqualsNoCase(value, "OpenGL") ? kOutputMethod_OpenGL :\\n'
    '                               StringEqualsNoCase(value, "OpenGLES2") ? kOutputMethod_R36S_GLES2 : kOutputMethod_SDL;', 1)
config_h.write_text(h, encoding="utf-8", newline="\\n")
config_c.write_text(c, encoding="utf-8", newline="\\n")

print("R36S instrumentation applied to build workspace (not tracked in git)")
