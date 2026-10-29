#ifndef R36S_WIDE_SCENE_H
#define R36S_WIDE_SCENE_H
#include <stddef.h>
#include <stdint.h>
typedef struct Ppu Ppu;

/* Host-side experiment. Does NOT mutate emulated PPU, gameplay RAM, or saves.
 * Capture registers BEFORE each original PPU scanline is rasterized,
 * because HDMA may change BG scroll/palette state across lines. */
void R36SWideScene_BeginFrame(void);
void R36SWideScene_CaptureLine(int y, const Ppu *ppu);
void R36SWideScene_Compose(uint8_t *dst, int pitch, int width, int height,
                           const uint8_t *native, int native_pitch);
#endif
