#ifndef R36S_BACKDROP_H
#define R36S_BACKDROP_H
#include <stdbool.h>

/* Purely decorative framebuffer background, never changes SNES pixels.
 * Original center 4:3 rendering still uses GL_NEAREST / SDL integer scaling.
 * Image path is relative to the working directory containing smw.ini. */
extern int r36s_use_backdrop;
extern char r36s_background_image[256];

bool R36SBackdrop_ParseUse(const char *text);
bool R36SBackdrop_ParseImage(const char *text);
const unsigned char *R36SBackdrop_LoadRGBA(int *width, int *height);
void R36SBackdrop_FreePixels(void);

#endif
