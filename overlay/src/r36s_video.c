#include "r36s_video.h"
#include <string.h>
#include <strings.h>

int r36s_viewport_16_9; /* 4:3 by default. */

bool R36SVideo_ParseViewport(const char *v) {
  if (!v) return false;
  if (!strcasecmp(v, "4:3") || !strcasecmp(v, "off") || !strcmp(v, "0")) {
    r36s_viewport_16_9=0; return true;
  }
  if (!strcasecmp(v, "16:9") || !strcmp(v, "1")) {
    r36s_viewport_16_9=1; return true;
  }
  return false;
}

/* Native 4:3 content centered inside an optional 16:9 host viewport.
   This deliberately does not claim a true expanded SMW world view. */
void R36SVideo_ContentRect(int W,int H,R36SViewport *dst) {
  if (!dst) return;
  if (W<1 || H<1) { dst->x=dst->y=dst->w=dst->h=0; return; }
  int frame_w=W,frame_h=H;
  if (r36s_viewport_16_9) {
    if ((long long)W*9 > (long long)H*16) frame_w=H*16/9;
    else frame_h=W*9/16;
  }
  /* A 16:9 framebuffer now contains real new scene pixels: display them.
     In 4:3 mode the stock picture is fitted without any cropping. */
  int game_w=frame_w,game_h=frame_h;
  if (!r36s_viewport_16_9) {
    if ((long long)frame_w*3 > (long long)frame_h*4) game_w=frame_h*4/3;
    else game_h=frame_w*3/4;
  }
  dst->w=game_w;dst->h=game_h;
  dst->x=(W-game_w)/2;dst->y=(H-game_h)/2;
}
