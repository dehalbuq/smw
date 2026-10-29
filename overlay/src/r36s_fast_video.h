#ifndef R36S_FAST_VIDEO_H
#define R36S_FAST_VIDEO_H
#include <stdbool.h>
typedef struct R36SRect { int x,y,w,h; } R36SRect;
extern int r36s_pixel_perfect;
extern int r36s_vsync;
bool R36SFast_ParsePixelPerfect(const char *text);
bool R36SFast_ParseVSync(const char *text);
void R36SFast_ContentRect(int display_w,int display_h,int source_w,int source_h,R36SRect *r);
void R36SFast_Pace(bool active);
#endif
