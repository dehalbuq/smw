#!/usr/bin/env bash
# Compile/test the *production* gles2_renderer.c on a real GLES2 Mesa context.
# No copyrighted ROM, generated C, or SNES runtime required.
set -euo pipefail
SMW_SOURCE="${1:?Usage: $0 /path/to/upstream-checkout}"
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/stubs/desktop"
cat > "$TMP/stubs/types.h" <<'EOF'
#pragma once
#include <stdint.h>
typedef uint8_t uint8;
EOF
cat > "$TMP/stubs/desktop/sdl_compat.h" <<'EOF'
#pragma once
#include <SDL.h>
static inline void snesrecomp_sdl_get_drawable_size(
    SDL_Window *w, int *width, int *height) {
  SDL_GL_GetDrawableSize(w, width, height);
}
EOF
cat > "$TMP/stubs/smw_renderer.h" <<'EOF'
#pragma once
#include <stdbool.h>
typedef struct SmwViewport { int width, extra; double aspect; } SmwViewport;
typedef struct SmwVideoSettings {
  bool enabled, adaptive_spawns;
  double aspect;
} SmwVideoSettings;
extern SmwVideoSettings g_smw_video;
extern SmwViewport g_smw_viewport;
void SmwDestination(SmwViewport view, int w, int h, int *x, int *y,
                    int *dw, int *dh);
EOF
cat > "$TMP/stubs/util.h" <<'EOF'
#pragma once
#include <stdbool.h>
#include <SDL.h>
#include "types.h"
struct RendererFuncs {
  bool (*Initialize)(SDL_Window *);
  void (*Destroy)(void);
  void (*GetOutputSize)(int *, int *);
  void (*BeginDraw)(int, int, uint8 **, int *);
  void (*EndDraw)(void);
  void (*Reconfigure)(void);
};
EOF
cat > "$TMP/stubs/config.h" <<'EOF'
#pragma once
#include <stdbool.h>
typedef struct Config {
  bool linear_filtering;
  bool ignore_aspect_ratio;
  const char *shader;
} Config;
extern Config g_config;
EOF

test -f "$SMW_SOURCE/src/port/gles2_renderer.c"
pkg-config --exists sdl2
cc -O2 -std=c11 -Wall -Wextra \
  -I"$TMP/stubs" -DSDL_GL_SwapWindow=smw_test_swap \
  "$SMW_SOURCE/src/port/gles2_renderer.c" \
  "$TEST_DIR/smw_gles2_smoke.c" \
  $(pkg-config --cflags --libs sdl2) -lGLESv2 -lEGL \
  -o "$TMP/smw_gles2_smoke"
file "$TMP/smw_gles2_smoke"
readelf -h "$TMP/smw_gles2_smoke" | grep -E 'Machine:|Class:'
if command -v xvfb-run >/dev/null 2>&1; then
  xvfb-run -a -s "-screen 0 1024x768x24" \
    env SDL_VIDEODRIVER=x11 LIBGL_ALWAYS_SOFTWARE=1 \
    timeout 40 "$TMP/smw_gles2_smoke"
else
  echo "ERROR: xvfb-run is required for cloud GPU smoke" >&2
  exit 1
fi
