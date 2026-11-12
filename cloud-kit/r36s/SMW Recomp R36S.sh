#!/usr/bin/env bash
# Experimental R36S / ArkOS / dArkOSRE / ArkOS4Clone launcher for SMW static recomp.
# Independent of the original dehalbuq/smw R36S port. No system library changes.
set -u

PORTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAMEDIR="$PORTS_DIR/smwrecompr36s"
BIN="$GAMEDIR/SuperMarioWorldSNESRecomp"
LOG="$GAMEDIR/smw-r36s.log"

mkdir -p "$GAMEDIR"
exec > >(tee "$LOG") 2>&1
echo "=== R36S SMW Recomp (experimental) ==="
date -u '+UTC %Y-%m-%dT%H:%M:%SZ'
uname -a
echo "glibc: $(getconf GNU_LIBC_VERSION 2>/dev/null || echo unavailable)"

if [[ ! -x "$BIN" ]]; then
  echo "FALHA: executavel ARM64 ausente ou sem permissao: $BIN"
  exit 2
fi
if [[ ! -r "$GAMEDIR/smw.sfc" ]]; then
  echo "FALHA: coloque sua ROM original smw.sfc na pasta $GAMEDIR"
  exit 3
fi

# PortMaster integration supports systems where SD card mounts at /roms or /roms2.
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
controlfolder=""
for candidate in /opt/system/Tools/PortMaster /opt/tools/PortMaster "$XDG_DATA_HOME/PortMaster" "$PORTS_DIR/PortMaster"; do
  if [[ -f "$candidate/control.txt" ]]; then
    controlfolder="$candidate"
    break
  fi
done

pm_used=0
cleanup_pm() {
  if [[ "$pm_used" = 1 ]] && declare -F pm_finish >/dev/null 2>&1; then
    pm_finish || true
  fi
}
trap cleanup_pm EXIT

if [[ -n "$controlfolder" ]]; then
  echo "PortMaster: $controlfolder"
  # control.txt is provided by the installed PortMaster, not by the game.
  # shellcheck disable=SC1090
  source "$controlfolder/control.txt"
  if [[ -n "${CFW_NAME:-}" ]] && [[ -f "$controlfolder/mod_${CFW_NAME}.txt" ]]; then
    # shellcheck disable=SC1090
    source "$controlfolder/mod_${CFW_NAME}.txt"
  fi
  if declare -F get_controls >/dev/null 2>&1; then
    get_controls || echo "AVISO: get_controls nao foi concluido"
  fi
  if [[ -n "${sdl_controllerconfig:-}" ]]; then
    export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"
  fi
  if [[ -n "${GPTOKEYB:-}" ]]; then
    echo "Atalho de saida: hotkey PortMaster + START (normalmente SELECT + START)"
    # GPTOKEYB is provided by PortMaster and kills this process on the hotkey.
    # As documented by PortMaster the variable may contain a command plus args.
    # shellcheck disable=SC2086
    $GPTOKEYB "SuperMarioWorldSNESRecomp" &
    pm_used=1
  else
    echo "AVISO: gptokeyb nao encontrado; use sair no menu do jogo"
  fi
  if declare -F pm_platform_helper >/dev/null 2>&1; then
    pm_platform_helper "$BIN" || echo "AVISO: pm_platform_helper nao foi concluido"
  fi
else
  echo "AVISO: control.txt do PortMaster nao encontrado."
  echo "O controle e o atalho de saida precisam de teste neste firmware."
fi

# Keep firmware's native KMSDRM/EGL/GLES2 driver; never bundle/override its libc.
export SDL_GAMECONTROLLER_ALLOW_STEAM_VIRTUAL_GAMEPAD=0
export HOME="${HOME:-/home/ark}"

cd "$GAMEDIR" || exit 4
echo "Launcher=ativo (para acessar Mods). Porta 640x480 / 4:3."
echo "SDL_VIDEODRIVER=${SDL_VIDEODRIVER:-auto}"
echo "Executando $BIN"
# By default, run without --rom: original recomp launcher provides Mods UI.
# If UI fails on the handheld, modify config.ini or use an explicit --rom
# in a follow-up diagnostics build; do not silently disable Mods here.
"$BIN"
rc=$?
echo "Processo encerrado com codigo $rc"
echo "Log: $LOG"
exit "$rc"
