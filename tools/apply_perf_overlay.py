#!/usr/bin/env python3
"""R36S 4:3 performance overlays, only after tools/apply_overlay.py."""
import sys, shutil, os
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
s = patch(s, '#include "r36s_quit_menu.h"', '#include "r36s_quit_menu.h"\n#include "r36s_fast_video.h"\n#include "r36s_gles2.h"\n#include "r36s_backdrop.h"', 'header')
s = patch(s, '  g_snes_width = (g_config.extended_aspect_ratio * 2 + 256);', '  g_snes_width = 256; /* R36S 4:3 native, no widescreen */', 'native-size')
s = patch(s, 'static SDL_Texture *g_texture;', 'static SDL_Texture *g_texture;\nstatic SDL_Texture *s_backdrop_texture;', 'sdl-backdrop-global')
s = patch(s, '  SDL_Renderer *renderer = SDL_CreateRenderer', '  SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "nearest");\n  SDL_Renderer *renderer = SDL_CreateRenderer', 'sdl-nearest')
s = patch(s, '  if (!g_config.ignore_aspect_ratio)\n    SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);', '  if (!g_config.ignore_aspect_ratio && !r36s_pixel_perfect)\n    SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);', 'sdl-logical')
s = patch(s, '  if (g_config.linear_filtering)\n    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "best");', '  /* Never use bilinear texture filtering on integer pixel art. */', 'sdl-quality')
s = patch(s,
    '  return true;\n}\n\nstatic void SdlRenderer_Destroy(void) {',
    """  /* Optional background decoded exactly once; no SDL_image dependency. */
  int bgw=0,bgh=0;
  const unsigned char *bg=R36SBackdrop_LoadRGBA(&bgw,&bgh);
  if(bg) {
    SDL_Surface *sf=SDL_CreateRGBSurfaceWithFormatFrom(
        (void*)bg,bgw,bgh,32,bgw*4,SDL_PIXELFORMAT_RGBA32);
    if(sf) {
      s_backdrop_texture=SDL_CreateTextureFromSurface(g_renderer,sf);
      SDL_FreeSurface(sf);
      if(s_backdrop_texture) SDL_SetTextureBlendMode(s_backdrop_texture, SDL_BLENDMODE_NONE);
    }
    if(!s_backdrop_texture)
      fprintf(stderr,"[BACKDROP] SDL texture creation failed: %s\\n",SDL_GetError());
    R36SBackdrop_FreePixels();
  }
  return true;
}

static void SdlRenderer_Destroy(void) {
  SDL_DestroyTexture(s_backdrop_texture);
  s_backdrop_texture=NULL;""",
    'sdl-load-backdrop')
s = patch(s, '  SDL_RenderClear(g_renderer);\n  SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, NULL);', """  SDL_SetRenderDrawColor(g_renderer, 0, 0, 0, 255);
  SDL_RenderClear(g_renderer);
  int sw=0,sh=0; SDL_GetRendererOutputSize(g_renderer,&sw,&sh);
  R36SRect r; R36SFast_ContentRect(sw,sh,g_snes_width,g_snes_height,&r);
  SDL_Rect dst={r.x,r.y,r.w,r.h};
  if(s_backdrop_texture)
    SDL_RenderCopy(g_renderer,s_backdrop_texture,NULL,NULL);
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
# The performance fork is native-only; do not mislabel its startup as
# "ROM comparison" just because an assets file contains the vanilla ROM.
s = patch(s,
          '"Starting with ROM comparison"',
          '"Running native C engine (comparison disabled)"',
          'native-startup-log')
if os.environ.get("R36S_RELEASE_BUILD") == "1":
    # Always cap simulated frames at 60, regardless of DisableFrameDelay
    # or render-skipping settings. There is no catch-up burst.
    s = patch(s,
              "R36SFast_Pace(!g_snes->disableRender && !g_config.disable_frame_delay);",
              "R36SFast_Pace(true);",
              "release-hard-60fps-cap")
p.write_text(s, encoding='utf-8', newline='\n')

# The overworld level id stays unchanged across pipe/sublevel transitions:
# log the *actual* level asset index before level loading.
pl=repo/'src/smw_05.c'
src=pl.read_text()
src=patch(src, '#include "variables.h"',
          '#include "variables.h"\n#include "r36s_diag.h"\n#include "r36s_vd1_pipe.h"\n#include <stdio.h>',
          'level-loader-includes')
src=patch(src, '  uint8 r2 = 0;  // todo: what is R2 here?',
          '  uint8 r2 = 0;  // todo: what is R2 here?\n'
          '  R36SVD1_OnLoadStart();', 'vd1-enter')
src=patch(src,
          "    if (flag_use_secondary_entrance) {\n      uint16 j = r14w;",
          "    R36SVD1_FixSecondaryEntrance(&r14w, v0);\n    if (flag_use_secondary_entrance) {\n      uint16 j = r14w;",
          'vd1-select-original-secondary')
src=patch(src,
          '  ptr_layer1_data = kLevelData_Layer1(r14w).ptr;',
          """  R36SVD1_OnResolveLevel(&r14w);
  {
    char info[240];
    snprintf(info, sizeof(info),
             "level_asset=%03x overworld=%02x sublevels=%u bonus=%u "
             "secondary=%u entrance=%u player=(%u,%u)",
             r14w, ow_level_number_lo, counter_sublevels_entered,
             flag_active_bonus_game, flag_use_secondary_entrance,
             misc_level_header_entrance_settings, player_xpos, player_ypos);
    R36SDiag_Message("LEVEL_ASSET", info);
  }
  R36SVD1_OnLoaded(r14w);
  ptr_layer1_data = kLevelData_Layer1(r14w).ptr;""", 'level-asset-index')
src=patch(src,
          '  return false;\n}\n\nvoid LoadLevel_HandleChocolateIsland2Gimmick()',
          '  R36SVD1_AfterLoad(r14w);\n'
          '  return false;\n}\n\nvoid LoadLevel_HandleChocolateIsland2Gimmick()',
          'vd1-after')

pl.write_text(src, encoding='utf-8', newline='\n')

# A screen exit may persist from a previously loaded sublevel in vanilla
# SMW. Trace *actual object writes* in Vanilla Dome 1 to identify which
# exit data the faulty pipe should use. No gameplay behavior change.
po=repo/'src/smw_0d.c'
objs=po.read_text()
objs=patch(objs,
           '#include "variables.h"',
           '#include "variables.h"\n#include "r36s_diag.h"\n#include <stdio.h>',
           'vd1-object-headers')
objs=patch(objs,
           '    flag_use_secondary_entrance = loadlvl_R11 >> 1;\n  }\n}',
           """    flag_use_secondary_entrance = loadlvl_R11 >> 1;
  }
  if (ow_level_number_lo == 0x3e && counter_sublevels_entered <= 2) {
    char note[210];
    snprintf(note, sizeof(note),
             "sublevels=%u screen=%u raw10=%02x raw11=%02x "
             "exit_to=%02x flags=%02x secondary=%u",
             (unsigned)counter_sublevels_entered, (unsigned)v2,
             (unsigned)loadlvl_R10, (unsigned)loadlvl_R11,
             (unsigned)blocks_object_number,
             (unsigned)misc_subscreen_exit_properties[v2],
             (unsigned)flag_use_secondary_entrance);
    R36SDiag_Message("VD1_EXIT_OBJECT", note);
  }
}""", 'vd1-object-exits')
po.write_text(objs, encoding='utf-8', newline='\n')

ph=repo/'src/config.h'
ch=ph.read_text()
ch=patch(ch, '  kOutputMethod_OpenGL,', '  kOutputMethod_OpenGL,\n  kOutputMethod_R36S_GLES2,', 'config-enum')
ph.write_text(ch, encoding='utf-8', newline='\n')
pc=repo/'src/config.c'
c=pc.read_text()
c=patch(c, '#include "config.h"', '#include "config.h"\n#include "r36s_fast_video.h"\n#include "r36s_backdrop.h"', 'config-header')
c=patch(c, '    } else if (StringEqualsNoCase(key, "IgnoreAspectRatio")) {', """    } else if (StringEqualsNoCase(key, "PixelPerfect")) {
      return R36SFast_ParsePixelPerfect(value);
    } else if (StringEqualsNoCase(key, "VSync")) {
      return R36SFast_ParseVSync(value);
    } else if (StringEqualsNoCase(key, "IgnoreAspectRatio")) {""", 'config-pixelperfect')
c=patch(c,
        '    } else if (StringEqualsNoCase(key, "PixelPerfect")) {',
        """    } else if (StringEqualsNoCase(key, "UseBackdrop")) {
      return R36SBackdrop_ParseUse(value);
    } else if (StringEqualsNoCase(key, "BackgroundImage")) {
      return R36SBackdrop_ParseImage(value);
    } else if (StringEqualsNoCase(key, "PixelPerfect")) {""",
        'config-backdrop')
c=patch(c, 'StringEqualsNoCase(value, "OpenGL") ? kOutputMethod_OpenGL : kOutputMethod_SDL;', 'StringEqualsNoCase(value, "OpenGL") ? kOutputMethod_OpenGL :\n                               StringEqualsNoCase(value, "OpenGLES2") ? kOutputMethod_R36S_GLES2 : kOutputMethod_SDL;', 'config-output')
pc.write_text(c, encoding='utf-8', newline='\n')

# Performance build uses native game only, not a second emulated instance.
pr=repo/'src/common_cpu_infra.c'
cr=pr.read_text()
cr=patch(cr, 'uint8 g_runmode = RM_BOTH;', 'uint8 g_runmode = RM_MINE;', 'native-engine')
pr.write_text(cr, encoding='utf-8', newline='\n')
for name in ('r36s_fast_video.c', 'r36s_fast_video.h', 'r36s_gles2.c', 'r36s_gles2.h',
             'r36s_vd1_pipe.c', 'r36s_vd1_pipe.h',
             'r36s_backdrop.c', 'r36s_backdrop.h'):
    shutil.copy2(base/'overlay/src'/name, repo/'src'/name)
print('R36S native 4:3 performance overlay: comparison off, no widescreen')
