#ifndef R36S_QUIT_MENU_H_
#define R36S_QUIT_MENU_H_
#include <stdbool.h>
#include <stdint.h>
#include <SDL.h>
bool R36SQuitMenu_HandleEvent(const SDL_Event *e);
void R36SQuitMenu_Update(void);
bool R36SQuitMenu_IsOpen(void);
bool R36SQuitMenu_WantsExit(void);
void R36SQuitMenu_Draw(uint8_t *pixels, int pitch, int width, int height, int render_scale);
#endif
