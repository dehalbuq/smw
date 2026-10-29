#!/usr/bin/env python3
"""R36S 4:3 performance overlays, only after tools/apply_overlay.py."""
import sys, shutil
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
base = Path(__file__).resolve().parent.parent

def patch(text, old, new, name):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{name}: expected one anchor, found {count}: {old[:100]!r}')
    return text.replace(old, new, 1)

p = repo / 'src/main.c'
s = p.read_text()
s = patch(s, '#include "r36s_quit_menu.h"', '#include "r36s_quit_menu.h"\n#include "r36s_fast_video.h"\n#include "r36s_gles2.h"', 'header')
s = patch(s, '  g_snes_width = (g_config.extended_aspect_ratio * 2 + 256);', '  g_snes_width = 256; /* R36S 4:3 native, no widescreen */', 'native-size')
s = patch(s, '  SDL_Renderer *renderer = SDL_CreateRenderer', '  SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "nearest");\n  SDL_Renderer *renderer = SDL_CreateRenderer', 'sdl-nearest')
s = patch(s, '  if (!g_config.ignore_aspect_ratio)\n    SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);', '  if (!g_config.ignore_aspect_ratio && !r36s_pixel_perfect)\n    SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);', 'sdl-logical')
s = patch(s, '  if (g_config.linear_filtering)\n    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "best");', '  /* Never use bilinear texture filtering on integer pixel art. */', 'sdl-quality')
s = patch(s, '  SDL_RenderClear(g_renderer);\n  SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, NULL);', """  SDL_SetRenderDrawColor(g_renderer, 0, 0, 0, 255);
  SDL_RenderClear(g_renderer);
  int sw=0,sh=0; SDL_GetRendererOutputSize(g_renderer,&sw,&sh);
  R36SRect r; R36SFast_ContentRect(sw,sh,g_snes_width,g_snes_height,&r);
  SDL_Rect dst={r.x,r.y,r.w,r.h};
  SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, &dst);""", 'sdl-dest')
s = patch(s, """  if (g_config.output_method == kOutputMethod_OpenGL) {
    g_win_flags |= SDL_WINDOW_OPENGL;
    OpenGLRenderer_Create(&g_renderer_funcs);
  } else {""", """  if (g_config.output_method == kOutputMethod_OpenGL) {
    g_win_flags |= SDL_WINDOW_OPENGL;
    OpenGLRenderer_Create(&g_renderer_funcs);
  }
#ifdef R36S_GLES2_SUPPORT
  else if (g_config.output_method == kOutputMethod_R36S_GLES2) {
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
    g_win_flags |= SDL_WINDOW_OPENGL;
    R36SGLES2Renderer_Create(&g_renderer_funcs);
  }
#endif
  else {""", 'renderer-select')
start = s.find("    // if vsync isn't working, delay manually")
end = s.find('\n  }\n\n  if (g_config.autosave)', start)
if start < 0 or end < 0:
    raise RuntimeError('stock 17/17/16 ms frame-pacing anchor missing')
s = s[:start] + '    R36SFast_Pace(!g_snes->disableRender && !g_config.disable_frame_delay);\n' + s[end:]
p.write_text(s, encoding='utf-8', newline='\n')

ph=repo/'src/config.h'
ch=ph.read_text()
ch=patch(ch, '  kOutputMethod_OpenGL,', '  kOutputMethod_OpenGL,\n  kOutputMethod_R36S_GLES2,', 'config-enum')
ph.write_text(ch, encoding='utf-8', newline='\n')
pc=repo/'src/config.c'
c=pc.read_text()
c=patch(c, '#include "config.h"', '#include "config.h"\n#include "r36s_fast_video.h"', 'config-header')
c=patch(c, '    } else if (StringEqualsNoCase(key, "IgnoreAspectRatio")) {', """    } else if (StringEqualsNoCase(key, "PixelPerfect")) {
      return R36SFast_ParsePixelPerfect(value);
    } else if (StringEqualsNoCase(key, "VSync")) {
      return R36SFast_ParseVSync(value);
    } else if (StringEqualsNoCase(key, "IgnoreAspectRatio")) {""", 'config-pixelperfect')
c=patch(c, 'StringEqualsNoCase(value, "OpenGL") ? kOutputMethod_OpenGL : kOutputMethod_SDL;', 'StringEqualsNoCase(value, "OpenGL") ? kOutputMethod_OpenGL :\n                               StringEqualsNoCase(value, "OpenGLES2") ? kOutputMethod_R36S_GLES2 : kOutputMethod_SDL;', 'config-output')
pc.write_text(c, encoding='utf-8', newline='\n')

# Performance build uses native game only, not a second emulated instance.
pr=repo/'src/common_cpu_infra.c'
cr=pr.read_text()
cr=patch(cr, 'uint8 g_runmode = RM_BOTH;', 'uint8 g_runmode = RM_MINE;', 'native-engine')
pr.write_text(cr, encoding='utf-8', newline='\n')
for name in ('r36s_fast_video.c', 'r36s_fast_video.h', 'r36s_gles2.c', 'r36s_gles2.h'):
    shutil.copy2(base/'overlay/src'/name, repo/'src'/name)
print('R36S native 4:3 performance overlay: comparison off, no widescreen')
