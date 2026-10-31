#!/bin/bash
# R36S / DarkOSRE / PortMaster — production launcher, without debug logs.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$ROOT/smw-r36s/smw" ]; then ROOT="$ROOT/smw-r36s"; fi
cd "$ROOT" || exit 1
[ -s smw_assets.dat ] || { echo "SMW R36S: faltando smw_assets.dat"; exit 2; }
mkdir -p saves playthrough
# The corrected vanilla secondary-entrance tables make speculative recovery
# unnecessary. Never silently teleport the player in production.
export SMW_R36S_VD1_PIPE_FIX=0
if [ -d libs ]; then export LD_LIBRARY_PATH="$PWD/libs:${LD_LIBRARY_PATH:-}"; fi

BINARY=./smw
ARGS=()
if grep -Eqi '^[[:space:]]*OutputMethod[[:space:]]*=[[:space:]]*OpenGLES2([[:space:]]|$)' smw.ini; then
  if [ -x ./smw-gles2 ] && ! ldd ./smw-gles2 2>&1 | grep -q 'not found'; then
    BINARY=./smw-gles2
  else
    # Fallback uses a separate config. Do not edit the user's smw.ini.
    sed -E 's/^[[:space:]]*OutputMethod[[:space:]]*=.*/OutputMethod = SDL-Software/' smw.ini > smw-fallback.ini
    ARGS=(--config smw-fallback.ini)
  fi
fi
[ -x "$BINARY" ] || { echo "SMW R36S: executavel ausente"; exit 126; }
exec "$BINARY" "${ARGS[@]}"
