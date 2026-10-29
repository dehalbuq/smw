#include "r36s_fast_video.h"
#include <SDL.h>
#include <stdio.h>
#include <strings.h>

/* Both defaults favour sharp/stable play. Disable VSync to compare latency;
 * disabling vsync may cause tearing on some RK3326 display stacks. */
int r36s_pixel_perfect=1;
int r36s_vsync=1;
static bool parse_bool(const char *text,int *value) {
  if(!text)return false;
  if(!strcasecmp(text,"1")||!strcasecmp(text,"true")||!strcasecmp(text,"yes")||!strcasecmp(text,"on")) {*value=1;return true;}
  if(!strcasecmp(text,"0")||!strcasecmp(text,"false")||!strcasecmp(text,"no")||!strcasecmp(text,"off")) {*value=0;return true;}
  return false;
}
bool R36SFast_ParsePixelPerfect(const char *text) {return parse_bool(text,&r36s_pixel_perfect);}
bool R36SFast_ParseVSync(const char *text) {return parse_bool(text,&r36s_vsync);}
void R36SFast_ContentRect(int W,int H,int sw,int sh,R36SRect *r) {
  if(!r)return;
  r->x=r->y=r->w=r->h=0;
  if(W<=0||H<=0||sw<=0||sh<=0)return;
  int w,h;
  if(r36s_pixel_perfect && W>=sw && H>=sh) {
    int scale=W/sw;
    if(H/sh<scale)scale=H/sh;
    w=sw*scale; h=sh*scale;
  } else {
    /* CRT-style 4:3 fallback, not true integer pixel scaling. */
    w=W;h=(int)((long long)W*3/4);
    if(h>H) {h=H;w=(int)((long long)H*4/3);}
  }
  r->x=(W-w)/2;r->y=(H-h)/2;r->w=w;r->h=h;
}
void R36SFast_Pace(bool active) {
  static Uint64 next_tick,last_report;
  static unsigned frames;
  if(!active) {next_tick=0;return;}
  const Uint64 freq=SDL_GetPerformanceFrequency();
  if(!freq)return;
  const Uint64 frame_ticks=freq/60;
  Uint64 now=SDL_GetPerformanceCounter();
  if(!next_tick)next_tick=now+frame_ticks;
  /* Avoid the stock 17/17/16 millisecond jitter and the risk of sleeping
     a second time after an already-blocking GLES2 swap. */
  if(now<next_tick) {
    Uint64 remaining=next_tick-now;
    if(remaining>freq/500) {
      Uint32 millis=(Uint32)(remaining*1000/freq);
      if(millis>1)SDL_Delay(millis-1);
    }
    while((now=SDL_GetPerformanceCounter())<next_tick) { /* short tail */ }
  }
  now=SDL_GetPerformanceCounter();
  if(!last_report)last_report=now;
  if(++frames==600) {
    double seconds=(double)(now-last_report)/(double)freq;
    fprintf(stderr,"[PERF] avg_fps=%.2f target=60 vsync=%d pixelperfect=%d\n",
            seconds>0.0 ? frames/seconds : 0.0, r36s_vsync,r36s_pixel_perfect);
    last_report=now;frames=0;
  }
  next_tick+=frame_ticks;
  if(now>next_tick+frame_ticks*2)next_tick=now+frame_ticks;
}
