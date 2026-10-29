#ifndef R36S_WIDE_SCENE_H
#define R36S_WIDE_SCENE_H
#include <stddef.h>
#include <stdint.h>

/* Experimental true horizontal Map16 scene expansion for vanilla SMW.
 * The original PPU continues to render exactly 256x224. All new pixels are
 * composed outside that frame and never alter gameplay RAM or savestates. */
void R36SWideScene_Compose(uint8_t *dst, int pitch, int width, int height,
                           const uint8_t *native, int native_pitch);
#endif
