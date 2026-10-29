#ifndef R36S_VIDEO_H
#define R36S_VIDEO_H
#include <stdbool.h>
typedef struct R36SViewport { int x,y,w,h; } R36SViewport;

/* Display-only layout. Real expanded scene rendering is NOT implemented yet.
   The gameplay PPU stays at native 256x224 and remains bit-for-bit unchanged. */
extern int r36s_viewport_16_9;
bool R36SVideo_ParseViewport(const char *value);
void R36SVideo_ContentRect(int output_w, int output_h, R36SViewport *dst);
#endif
