#!/bin/bash
# Run this on the handheld: bash diagnose_r36s.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/r36s-diagnostics.txt"
{
  echo "=== SMW Recomp R36S diagnostics ==="
  date -u
  uname -a
  (cat /etc/os-release || true) 2>/dev/null
  echo "GLIBC: $(getconf GNU_LIBC_VERSION 2>&1 || true)"
  echo "LIBC: $(ls -l /lib/aarch64-linux-gnu/libc.so.6 /usr/lib/libc.so.6 2>/dev/null || true)"
  echo "SDL_VIDEODRIVER: ${SDL_VIDEODRIVER:-unset}"
  echo "SDL_GAMECONTROLLERCONFIG length: ${#SDL_GAMECONTROLLERCONFIG}"
  echo "KMS/DRM:"
  ls -l /dev/dri/* 2>/dev/null || true
  echo "Framebuffer:"
  ls -l /dev/fb* 2>/dev/null || true
  echo "Display modes:"
  cat /sys/class/drm/*/modes 2>/dev/null || true
  echo "Memory:"
  free -m 2>/dev/null || true
  echo "Binary file:"
  file "$HERE/SuperMarioWorldSNESRecomp" 2>/dev/null || true
  echo "Dynamic linker / NEEDED:"
  readelf -l "$HERE/SuperMarioWorldSNESRecomp" 2>/dev/null | grep 'interpreter' || true
  readelf -d "$HERE/SuperMarioWorldSNESRecomp" 2>/dev/null | grep NEEDED || true
  echo "Version needs:"
  readelf --version-info "$HERE/SuperMarioWorldSNESRecomp" 2>/dev/null | grep -E 'GLIBC_|GLIBCXX_' | sort -u || true
  echo "ldd:"
  ldd "$HERE/SuperMarioWorldSNESRecomp" 2>&1 || true
  echo "PortMaster paths:"
  ls -ld /opt/system/Tools/PortMaster /opt/tools/PortMaster /roms/ports/PortMaster 2>/dev/null || true
  echo "Last log:"
  tail -n 120 "$HERE/smw-r36s.log" 2>/dev/null || true
} > "$OUT" 2>&1
echo "Diagnostics saved to $OUT"
