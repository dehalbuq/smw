#include "r36s_quit_menu.h"
#include "r36s_diag.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* DarkOSRE / GO-Super Gamepad: physical SELECT=b12, START=b13.
 * These are missing from the normal SDL GameController mapping in the user's log.
 * Overrides use the same environment variables as the main input fallback. */
static int menu_open, exit_requested, select_down, start_down, combo_active;
static uint32_t select_since, combo_since;

static int raw_button(const char *key, int default_number) {
  const char *s = getenv(key);
  if (!s || !*s) return default_number;
  char *end;
  long number = strtol(s, &end, 10);
  return !*end && number >= 0 && number <= 255 ? (int)number : default_number;
}
static void menu_open_now(const char *why) {
  if (!menu_open) { menu_open = 1; R36SDiag_Message("EXIT_MENU", why); }
}
static void menu_cancel(void) {
  if (menu_open) { menu_open = 0; R36SDiag_Message("EXIT_MENU", "Cancel; return to game"); }
}
static void menu_exit(const char *why) {
  if (!exit_requested) { exit_requested = 1; R36SDiag_Message("EXIT_REQUEST", why); }
}

bool R36SQuitMenu_HandleEvent(const SDL_Event *e) {
  int pressed, select = 0, start = 0, accept = 0, cancel = 0;
  if (e->type == SDL_KEYDOWN) {
    if (e->key.repeat) return menu_open != 0;
    SDL_Keycode k = e->key.keysym.sym;
    if (k == SDLK_ESCAPE) {
      if (menu_open) menu_cancel(); else menu_open_now("ESC key");
      return true;
    }
    if (menu_open) {
      if (k == SDLK_RETURN || k == SDLK_KP_ENTER || k == SDLK_SPACE)
        menu_exit("Keyboard confirmation");
      else if (k == SDLK_BACKSPACE) menu_cancel();
      return true;
    }
    return false;
  }
  if (e->type == SDL_KEYUP) return menu_open != 0;
  if (e->type == SDL_JOYBUTTONDOWN || e->type == SDL_JOYBUTTONUP) {
    pressed = e->type == SDL_JOYBUTTONDOWN;
    select = e->jbutton.button == raw_button("SMW_R36S_SELECT_BUTTON", 12);
    start = e->jbutton.button == raw_button("SMW_R36S_START_BUTTON", 13);
    accept = e->jbutton.button == 0;
    cancel = e->jbutton.button == 1;
  } else if (e->type == SDL_CONTROLLERBUTTONDOWN || e->type == SDL_CONTROLLERBUTTONUP) {
    pressed = e->type == SDL_CONTROLLERBUTTONDOWN;
    select = e->cbutton.button == SDL_CONTROLLER_BUTTON_BACK ||
             e->cbutton.button == SDL_CONTROLLER_BUTTON_GUIDE;
    start = e->cbutton.button == SDL_CONTROLLER_BUTTON_START;
    accept = e->cbutton.button == SDL_CONTROLLER_BUTTON_A;
    cancel = e->cbutton.button == SDL_CONTROLLER_BUTTON_B;
  } else return false;

  int previously_open = menu_open, was_select_down = select_down;
  uint32_t now = SDL_GetTicks();
  if (select) {
    select_down = pressed;
    if (pressed && !was_select_down) select_since = now;
  }
  if (start) start_down = pressed;

  if (select_down && start_down) {
    if (!combo_active) { combo_active = 1; combo_since = now; }
  } else combo_active = 0;

  if (previously_open && pressed) {
    if (start || accept) menu_exit("Confirmed by START/A");
    else if ((select && !was_select_down) || cancel) menu_cancel();
  } else if (!previously_open && select_down && start_down) {
    menu_open_now("SELECT + START opened exit menu");
  }
  /* Always pass release events to the game, avoiding stuck key states. */
  if (!pressed) return false;
  return previously_open || menu_open;
}
void R36SQuitMenu_Update(void) {
  uint32_t now = SDL_GetTicks();
  if (select_down && !menu_open && (uint32_t)(now - select_since) >= 950)
    menu_open_now("Held SELECT for 0.95 second");
  if (combo_active && (uint32_t)(now - combo_since) >= 3000)
    menu_exit("Emergency exit: SELECT + START held 3 seconds");
}
bool R36SQuitMenu_IsOpen(void) { return menu_open != 0; }
bool R36SQuitMenu_WantsExit(void) { return exit_requested != 0; }

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
void R36SQuitMenu_Draw(uint8_t *buf,int pitch,int width,int height,int render_scale) {
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
