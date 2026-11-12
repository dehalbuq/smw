#!/usr/bin/env bash
# Configure the real AArch64 SDL2/GLES2 CMake project without a copyrighted ROM.
# A temporary synthetic source exists ONLY to satisfy CMake's required src/gen glob.
# This is strictly NOT a game build and it does not generate a playable executable.
set -euo pipefail
SOURCE="${1:?Usage: run_cmake_preflight.sh /path/to/checkout}"
BUILD_DIR="${2:?Usage: run_cmake_preflight.sh /path/to/checkout /path/to/build}"
cd "$SOURCE"
mkdir -p src/gen
STUB="src/gen/__emuelec_cloud_cmake_preflight_only.c"
if [[ -e "$STUB" ]]; then
  echo "ERROR: synthetic preflight source unexpectedly exists" >&2
  exit 1
fi
if find src/gen -maxdepth 1 -type f -name '*.c' | grep -q .; then
  echo "ERROR: preflight refuses to run in a checkout containing generated game C" >&2
  exit 1
fi
cleanup() { rm -f "$STUB"; }
trap cleanup EXIT
printf '/* preflight placeholder, not game CPU code */\n' > "$STUB"
cmake -S . -B "$BUILD_DIR" -G Ninja \
  -DSMW_EMUELEC_GLES2=ON \
  -DSNESRECOMP_SDL_BACKEND=SDL2 \
  -DSMW_BUNDLE_FALCON_CACHE_HELPER=OFF \
  -DSMW_NETPLAY_ICE=OFF \
  -DSNESRECOMP_ENABLE_LUA=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
python3 - "$BUILD_DIR" <<'PY'
import json
import pathlib
import sys
b = pathlib.Path(sys.argv[1])
cache = (b / 'CMakeCache.txt').read_text()
required = [
    'SMW_EMUELEC_GLES2:BOOL=ON',
    'SNESRECOMP_SDL_BACKEND:STRING=SDL2',
    'SMW_BUNDLE_FALCON_CACHE_HELPER:BOOL=OFF',
    'SMW_NETPLAY_ICE:BOOL=OFF',
]
missing = [k for k in required if k not in cache]
if missing:
    raise SystemExit("FAIL CMake cache options: " + ", ".join(missing))
commands = json.loads((b / 'compile_commands.json').read_text())
paths = [x['file'].replace('\\', '/') for x in commands]
if not any(x.endswith('/src/port/gles2_renderer.c') for x in paths):
    raise SystemExit('FAIL missing production GLES2 source')
if any(x.endswith('/src/opengl.c') for x in paths):
    raise SystemExit('FAIL desktop OpenGL3 presenter remains in compile list')
if any(x.endswith('/third_party/gl_core/gl_core_3_1.c') for x in paths):
    raise SystemExit('FAIL GL3 core compilation remains in compile list')
if not any('/recomp-ui/' in x or '/recomp_ui/' in x for x in paths):
    raise SystemExit('FAIL recomp-ui launcher sources missing')
if not any(x.endswith('/src/smw_renderer.c') for x in paths):
    raise SystemExit('FAIL adaptive widescreen rasterizer missing')
if not any('/src/mods/coop/' in x for x in paths):
    raise SystemExit('FAIL native co-op source missing')
print('PASS CMAKE_EMUELEC_PREFLIGHT: AArch64 SDL2 GLES2 + launcher + widescreen + native coop')
print(f'Compile units: {len(commands)}; synthetic C is NOT an executable')
PY
