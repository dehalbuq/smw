#include <SDL.h>
#include <SDL_system.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* SDLActivity calls SDL_main() through libSDL2 Android JNI bridge.
 * The original game keeps a normal main() symbol via SDL_MAIN_HANDLED. */
extern int main(int argc, char **argv);

static int copy_legal_rom_asset(const char *path) {
    SDL_RWops *source = SDL_RWFromFile("smw.sfc", "rb");
    if (!source) {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION,
                     "Unable to open private ROM asset: %s", SDL_GetError());
        return -1;
    }
    FILE *output = fopen(path, "wb");
    if (!output) { SDL_RWclose(source); return -1; }
    unsigned char buffer[16384];
    size_t size;
    int bad = 0;
    while ((size = SDL_RWread(source, buffer, 1, sizeof buffer)) > 0) {
        if (fwrite(buffer, 1, size, output) != size) { bad = 1; break; }
    }
    if (fclose(output)) bad = 1;
    SDL_RWclose(source);
    if (bad) unlink(path);
    return bad ? -1 : 0;
}

__attribute__((visibility("default"))) int SDL_main(int argc, char **argv) {
    (void)argc; (void)argv;
    const char *base = SDL_AndroidGetInternalStoragePath();
    if (!base || !*base || chdir(base)) return 2;
    setenv("HOME", base, 1);
    setenv("XDG_DATA_HOME", base, 1);
    setenv("SMW_RENDER_ASPECT", "16:9", 1);
    setenv("SMW_ENEMY_SPAWN", "adaptive", 1);
    setenv("SNESRECOMP_NO_LAUNCHER", "1", 1);
    /* Keep debug CPU trace memory bounded on low-RAM Android TVs. */
    setenv("SNESRECOMP_CPU_TRACE_RING_ENTRIES", "131072", 1);

    char rom[2048];
    if (snprintf(rom, sizeof(rom), "%s/smw.sfc", base) >= (int)sizeof(rom))
        return 3;
    if (access(rom, R_OK) && copy_legal_rom_asset(rom)) return 4;

    char *args[] = {"libmain.so", "--no-launcher", "--rom", rom, NULL};
    return main(4, args);
}
