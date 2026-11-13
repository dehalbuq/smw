#include <SDL.h>

/* PUBLIC CI ONLY: smoke-test Android SDL Activity and native ABI.
 * This deliberately does not implement the game or load a ROM. */
__attribute__((visibility("default"))) int SDL_main(int argc, char **argv) {
    (void)argc; (void)argv;
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER) < 0) return 1;
    SDL_Window *w = SDL_CreateWindow("SMW Android TV SDL preflight",
                         SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
                         1280, 720, SDL_WINDOW_SHOWN | SDL_WINDOW_FULLSCREEN);
    if (!w) { SDL_Quit(); return 2; }
    SDL_Delay(100);
    SDL_DestroyWindow(w);
    SDL_Quit();
    return 0;
}
