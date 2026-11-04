#include "android_quit_menu.h"
#include <SDL.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

/* Android-only adaptation of the on-frame R36S exit overlay.
 * The controller is sampled directly every frame, including the PG-9068
 * whose Android TV firmware sometimes drops SDL_CONTROLLERBUTTON* events.
 * Do not make the underlying game handle menu button presses. */
static bool menu_open;
static bool exit_requested;
static bool combo_latched;
static bool wait_for_chord_release;
static bool prior_select, prior_start, prior_accept, prior_cancel;
static Uint32 combo_started_at;

/* SDLActivity may launch native main twice without unloading libmain.so.
 * Never let a previous game's exit_requested flag kill the new session. */
void AndroidQuitMenu_Reset(void) {
  menu_open = false;
  exit_requested = false;
  combo_latched = false;
  wait_for_chord_release = false;
  prior_select = false;
  prior_start = false;
  prior_accept = false;
  prior_cancel = false;
  combo_started_at = 0;
}

void AndroidQuitMenu_Poll(bool select_down, bool start_down,
                          bool accept_down, bool cancel_down) {
  const bool chord = select_down && start_down;
  const Uint32 now = SDL_GetTicks();

  if (!menu_open && chord && !combo_latched) {
    menu_open = true;
    combo_latched = true;
    wait_for_chord_release = true;
    combo_started_at = now;
  } else if (menu_open) {
    // R36S has a 3-second emergency chord; keep it for a stuck menu.
    if (chord && combo_latched &&
        (Uint32)(now - combo_started_at) >= 3000)
      exit_requested = true;

    // Both original buttons must be released before a confirmation can
    // happen, so START never immediately closes the dialog that it opened.
    if (wait_for_chord_release) {
      if (!select_down && !start_down)
        wait_for_chord_release = false;
    } else if ((start_down && !prior_start) ||
               (accept_down && !prior_accept)) {
      exit_requested = true;
    } else if ((select_down && !prior_select) ||
               (cancel_down && !prior_cancel)) {
      menu_open = false;
    }
  }

  if (!select_down && !start_down)
    combo_latched = false;
  prior_select = select_down;
  prior_start = start_down;
  prior_accept = accept_down;
  prior_cancel = cancel_down;
}

bool AndroidQuitMenu_IsOpen(void) { return menu_open; }
bool AndroidQuitMenu_WantsExit(void) { return exit_requested; }

/* Compact 5x5 bitmap font: row byte per hexadecimal pair, 5 rows per glyph.
 * Renders directly onto the PPU frame; no SDL_ttf, mouse or extra packages. */
static const char *glyph[26] = {
  "0e111f1111","1e111e111e","0f1010100f","1e1111111e",
  "1f101e101f","1f101e1010","0f1013110f","11111f1111",
  "1f0404041f","070202120c","1112161211","101010101f",
  "111b151111","1119151311","0e1111110e","1e111e1010",
  "0e1111150f","1e111e1211","0f100e011e","1f04040404",
  "111111110e","1111110a04","1111151b11","110a040a11",
  "11110a0404","1f0204081f"
};
static int bits_for(char c, int y) {
  if (c >= 'A' && c <= 'Z') {
    const char *s = glyph[c - 'A'] + y*2;
    unsigned a, b;
    a = *s >= 'a' ? *s - 'a' + 10 : *s - '0';
    b = s[1] >= 'a' ? s[1] - 'a' + 10 : s[1] - '0';
    return ((a << 4) | b) & 31;
  }
  if (c == '=') return (y == 1 || y == 3) ? 31 : 0;
  if (c == '?') { static const int r[5]={14,17,2,4,4}; return r[y]; }
  if (c == '+') return y == 2 ? 31 : 4;
  return 0;
}
static void fill(uint8_t *buf, int pitch, int width, int height,
                 int x, int y, int w, int h, uint32_t color) {
  int x0 = x > 0 ? x : 0, y0 = y > 0 ? y : 0;
  int x1 = x + w < width ? x+w : width;
  int y1 = y + h < height ? y+h : height;
  for (int yy=y0; yy<y1; yy++) {
    uint32_t *dst = (uint32_t *)(void *)(buf + (size_t)yy*pitch);
    for (int xx=x0; xx<x1; xx++) dst[xx]=color;
  }
}
static void text_line(uint8_t *buf, int pitch, int width, int height,
                      int y, const char *str, int scale, uint32_t color) {
  int len=(int)strlen(str);
  int x=(width - len*6*scale)/2;
  for (int i=0; i<len; i++) for (int row=0; row<5; row++) {
    int bits=bits_for(str[i],row);
    for (int b=0;b<5;b++) if (bits & (1 << (4-b)))
      fill(buf,pitch,width,height,x+(i*6+b)*scale,y+row*scale,scale,scale,color);
  }
}
void AndroidQuitMenu_Draw(uint8_t *buf,int pitch,int width,int height,int render_scale) {
  if (!menu_open || !buf || pitch <= 0) return;
  int s=render_scale>0 ? render_scale : 1;
  int bw=236*s,bh=108*s,x=(width-bw)/2,y=(height-bh)/2;
  fill(buf,pitch,width,height,x,y,bw,bh,0xff09121f);
  fill(buf,pitch,width,height,x,y,bw,3*s,0xff53d1da);
  fill(buf,pitch,width,height,x,y+bh-3*s,bw,3*s,0xff53d1da);
  text_line(buf,pitch,width,height,y+10*s,"SAIR DO JOGO?",s*2,0xffeeeeee);
  text_line(buf,pitch,width,height,y+37*s,"START = SAIR",s*2,0xffffff50);
  text_line(buf,pitch,width,height,y+58*s,"SELECT = VOLTAR",s*2,0xffeeeeee);
  text_line(buf,pitch,width,height,y+79*s,"A = SIM  B = NAO",s*2,0xffc5e9eb);
}
