#!/usr/bin/env bash
# Executed INSIDE the native AArch64 Debian Buster (glibc 2.28) container.
# Source checkout must already contain ROM-generated C in src/gen/.
# ROM itself must have been deleted before entering this container.
set -euo pipefail
SOURCE_DIR="${1:-/src}"
PORT_CODE="${2:-/port-code}"
OUTPUT_ROOT="${3:-/output}"
cd "$SOURCE_DIR"

test "$(uname -m)" = aarch64
test "$(getconf GNU_LIBC_VERSION)" = "glibc 2.28"
test ! -e ./smw.sfc
compgen -G "src/gen/*.c" >/dev/null || { echo 'FAIL: no generated C; run regen on host first' >&2; exit 2; }
test -f src/port/gles2_renderer.c
test -f "$PORT_CODE/cloud-kit/r36s/SMW Recomp R36S.sh"

export SMW_BUILD_DIR=build-r36s-gles2
export SMW_BUNDLE_FALCON_CACHE_HELPER=OFF
export SMW_NETPLAY_ICE=OFF
export SMW_ALLOW_UNVERIFIED_ABI=1
export JOBS="${JOBS:-2}"
export CMAKE_BUILD_PARALLEL_LEVEL="$JOBS"
export MAKEFLAGS="-j$JOBS"
# Marks the build as R36S, not EmuELEC, in the runtime.
sed -i 's/emuelec48-gles2/r36s-gles2-glibc228/' tools/build_emuelec.sh
bash tools/build_emuelec.sh

GAME_BIN="$SMW_BUILD_DIR/SuperMarioWorldSNESRecomp"
test -f "$GAME_BIN"
readelf -h "$GAME_BIN" | grep -q 'Machine:.*AArch64'
if readelf -d "$GAME_BIN" | grep -q 'Shared library: \[libGL.so'; then
  echo 'FAIL: the binary links desktop libGL, incompatible with GLES-only R36S' >&2
  exit 4
fi

python3 - "$GAME_BIN" <<'PY'
import pathlib
import re
import subprocess
import sys
exe = pathlib.Path(sys.argv[1])
versions = subprocess.check_output(["readelf", "--version-info", str(exe)], universal_newlines=True)
glibc = [tuple(map(int, x)) for x in re.findall(r"GLIBC_(\d+)\.(\d+)", versions)]
if not glibc:
    sys.exit("FAIL: GLIBC version requirements not found")
maxver = max(glibc)
print("GLIBC requirement maximum: %d.%d" % maxver)
if maxver > (2, 30):
    sys.exit("FAIL: GLIBC too new for R36S ArkOS 2.30")
print("PASS R36S_GLIBC_MAX<=2.30")
PY

# Pack assets and mods staged by CMake; never include copyrighted ROM.
INNER="$OUTPUT_ROOT/smwrecompr36s"
mkdir -p "$INNER" "$INNER/licenses"
cp "$GAME_BIN" "$INNER/SuperMarioWorldSNESRecomp"
for dir in assets mods shader_presets; do
  [[ ! -d "$SMW_BUILD_DIR/$dir" ]] || cp -a "$SMW_BUILD_DIR/$dir" "$INNER/"
done
cp "$PORT_CODE/cloud-kit/r36s/config.ini" "$INNER/config.ini"
cp "$PORT_CODE/cloud-kit/r36s/diagnose_r36s.sh" "$INNER/diagnose_r36s.sh"
cp "$PORT_CODE/cloud-kit/r36s/SMW Recomp R36S.sh" "$OUTPUT_ROOT/SMW Recomp R36S.sh"
cp "$PORT_CODE/cloud-kit/r36s/port.json" "$OUTPUT_ROOT/port.json"
cp "$PORT_CODE/cloud-kit/r36s/gameinfo.xml" "$OUTPUT_ROOT/gameinfo.xml"
cp "$PORT_CODE/cloud-kit/r36s/README.md" "$OUTPUT_ROOT/README.md"
[[ ! -f LICENSE ]] || cp LICENSE "$INNER/licenses/SUPERMARIOWORLDRECOMP-LICENSE.txt"
[[ ! -f PERMISSIONS.md ]] || cp PERMISSIONS.md "$INNER/licenses/PERMISSIONS.md"

{
  echo "SMW Recomp R36S isolated AArch64 SDL2 GLES2 experimental build"
  echo "Built in Debian Buster glibc 2.28. Max GLIBC <= 2.30 required."
  echo "ROM is not included. Do not replace firmware libraries."
  echo "Firmware, SDL2/GLES2 loader and performance are not hardware validated."
  echo
  file "$GAME_BIN"
  readelf -h "$GAME_BIN"
  readelf -d "$GAME_BIN"
  readelf --version-info "$GAME_BIN"
} > "$INNER/ABI-REPORT.txt"

find "$OUTPUT_ROOT" -type f \( -iname '*.sfc' -o -iname '*.smc' -o -iname '*.z64' -o -iname '*.n64' \) > /tmp/r36s-rom-files.txt
if [[ -s /tmp/r36s-rom-files.txt ]]; then
  echo "FAIL: game ROM was found in output; refusing publication" >&2
  exit 5
fi

chmod +x "$OUTPUT_ROOT/SMW Recomp R36S.sh" "$INNER/SuperMarioWorldSNESRecomp" "$INNER/diagnose_r36s.sh"
echo "PASS R36S_PORTMASTER_PACKAGE: standalone aarch64 with 4:3 defaults"
echo "OUTPUT_ROOT=$OUTPUT_ROOT"
