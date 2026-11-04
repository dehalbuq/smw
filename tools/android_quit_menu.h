#ifndef SMW_ANDROID_QUIT_MENU_H
#define SMW_ANDROID_QUIT_MENU_H
#include <stdbool.h>
#include <stdint.h>
void AndroidQuitMenu_Poll(bool select_down, bool start_down,
                          bool accept_down, bool cancel_down);
bool AndroidQuitMenu_IsOpen(void);
bool AndroidQuitMenu_WantsExit(void);
void AndroidQuitMenu_Draw(uint8_t *pixels, int pitch, int width, int height,
                          int render_scale);
#endif
