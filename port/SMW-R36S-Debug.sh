#!/bin/bash
# R36S / DarkOSRE / PortMaster manual debug launcher.
set -u
BASE="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$BASE/smw-r36s/smw" ]; then GAMEDIR="$BASE/smw-r36s"; else GAMEDIR="$BASE"; fi
cd "$GAMEDIR" || exit 1
mkdir -p logs saves playthrough
STAMP="$(date +%Y%m%d-%H%M%S 2>/dev/null || echo session)"
RUNLOG="logs/run-${STAMP}.log"
exec >> "$RUNLOG" 2>&1
printf '=== SMW R36S DEBUG SESSION %s ===\n' "$STAMP"
printf 'working_dir=%s\n' "$PWD"
uname -a || true
printf 'architecture='; uname -m || true
printf 'glibc='; getconf GNU_LIBC_VERSION 2>&1 || true
printf 'memory='; free -m 2>&1 || true
BINARY="./smw"
CONFIG_ARGS=()
if grep -Eqi '^[[:space:]]*OutputMethod[[:space:]]*=[[:space:]]*OpenGLES2([[:space:]]|$)' smw.ini 2>/dev/null; then
  if [ -x ./smw-gles2 ] && ! ldd ./smw-gles2 2>&1 | grep -q 'not found'; then
    BINARY="./smw-gles2"
    echo 'R36S_GLES2=selected'
  else
    echo 'R36S_GLES2=missing: selecting software renderer'
    # Never mutate the user's real configuration file on fallback.
    sed -E 's/^[[:space:]]*OutputMethod[[:space:]]*=.*/OutputMethod = SDL-Software/' smw.ini > smw-fallback.ini
    CONFIG_ARGS=(--config smw-fallback.ini)
  fi
fi
printf 'binary info:\n'; file "$BINARY" 2>&1 || true
printf 'binary dependencies:\n'; ldd "$BINARY" 2>&1 || true
printf 'sdl_env: video=%s audio=%s\n' "${SDL_VIDEODRIVER:-system-default}" "${SDL_AUDIODRIVER:-system-default}"
printf 'VD1_PIPE_FIX=%s (1=experimental route recovery; 0=disabled)\n' "${SMW_R36S_VD1_PIPE_FIX:-1}"
if [ ! -x "$BINARY" ]; then echo 'ERROR: smw executable missing or not executable'; exit 126; fi
if [ ! -s smw_assets.dat ]; then echo 'ERROR: smw_assets.dat missing'; exit 2; fi
if [ -d libs ]; then export LD_LIBRARY_PATH="$PWD/libs:${LD_LIBRARY_PATH:-}"; fi
ulimit -c 0 2>/dev/null || true
if [ "${SMW_EXTERNAL_ROM:-0}" = '1' ] && [ -s smw.sfc ]; then
  echo 'ROM: explicitly provided smw.sfc'
  "$BINARY" "${CONFIG_ARGS[@]}" smw.sfc
else
  echo 'ROM: smw_assets.dat (comparison only when ROM was included in extraction)'
  "$BINARY" "${CONFIG_ARGS[@]}"
fi
status=$?
printf 'game_exit_status=%d\n' "$status"
exit "$status"
