#ifndef R36S_DIAG_H_
#define R36S_DIAG_H_
#include <stdint.h>
#include <stddef.h>

/* R36S logger: no dependency on the video/audio renderer. */
void R36SDiag_Init(void);
void R36SDiag_Message(const char *type, const char *message);
void R36SDiag_Assets(size_t size, unsigned int count);
void R36SDiag_BeforeFrame(uint32_t frame, uint32_t inputs);
void R36SDiag_AfterFrame(uint32_t frame, uint32_t inputs, int mismatch_count, uint8_t game_id);
void R36SDiag_Close(void);
#endif
