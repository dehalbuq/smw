#!/usr/bin/env bash
# SMW Recomp R36S - local Linux build (x86_64 or ARM64).
# Does not require GitHub Actions, private repo access, or WSL.
# The user provides a legally obtained Super Mario World (USA) smw.sfc.
set -Eeuo pipefail

GITHUB_OWNER="dehalbuq"
PORT_REPO="https://github.com/$GITHUB_OWNER/smw.git"
SOURCE_REPO="https://github.com/mstan/SuperMarioWorldRecomp.git"
SOURCE_REVISION="afc5850ff96ffc7edb63a31725cb5eeacae017bb"
KIT_SHA256="e1bb6235bd584df602f5850884937c4f9486f1b7d4cac49309f7c5844a516030"
ROM_SHA256="0838e531fe22c077528febe14cb3ff7c492f1f5fa8de354192bdff7137c27f5b"

COMMAND=""
if (( $# > 0 )); then COMMAND="$1"; shift; fi

usage() {
  cat <<'USAGE'
USO:
  bash COMPILAR_SMW_R36S_LINUX.sh preparar
  bash COMPILAR_SMW_R36S_LINUX.sh compilar "/caminho/para/smw.sfc"

OPCIONAL:
  SMW_WORKDIR="$HOME/SMW-R36S"    pasta de trabalho
  JOBS=1                          reduz consumo de memoria durante compilacao
  FORCAR_REGEN=1                  regenera codigo C no segundo build

REQUER Linux Ubuntu/Mint/Debian com apt, PC x86_64 ou ARM64, internet,
espaco em disco para submodulos e container, e sua ROM USA original.
O ZIP nao inclui a ROM e nao altera o firmware.
USAGE
}
case "$COMMAND" in
  preparar|compilar) ;;
  *) usage; exit 2 ;;
esac

for command in bash git python3 curl sha256sum tar base64; do
  if [[ "$COMMAND" == "preparar" ]]; then break; fi
  command -v "$command" >/dev/null || { echo "FALTA: $command; execute 'preparar' primeiro" >&2; exit 2; }
done

prepare() {
  command -v apt-get >/dev/null || { echo "Este instalador foi escrito para Ubuntu/Mint/Debian (apt)." >&2; exit 2; }
  echo "Preparando ferramentas no Linux local (nao altera particoes)."
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    git curl ca-certificates build-essential pkg-config cmake ninja-build \
    python3 python3-pip python3-venv python3-dev unzip zip file binutils xz-utils \
    docker.io qemu-user-static binfmt-support
  if command -v systemctl >/dev/null; then
    sudo systemctl enable --now docker
  fi
  if ! command -v rustup >/dev/null; then
    echo "Instalando Rust via rustup oficial (gera codigo C da CPU SNES)."
    curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs -o "$HOME/rustup-init-r36s.sh"
    sh "$HOME/rustup-init-r36s.sh" -y --profile minimal --default-toolchain stable
    rm -f "$HOME/rustup-init-r36s.sh"
  fi
  if [[ -f "$HOME/.cargo/env" ]]; then
    # shellcheck disable=SC1091
    source "$HOME/.cargo/env"
  fi
  rustup toolchain install stable --profile minimal
  echo "Rust: $(rustc --version)"
  echo "Docker: $(sudo docker --version)"
  if [[ "$(uname -m)" == "x86_64" ]]; then
    if command -v update-binfmts >/dev/null; then
      sudo update-binfmts --enable qemu-aarch64 || true
    fi
  fi
  echo "Verificando containers ARM64 / emulacao QEMU, se necessario..."
  sudo docker run --rm --platform linux/arm64 debian:buster \
    sh -c 'test "$(uname -m)" = aarch64 && echo "PASS ARM64 Docker"'
  echo "PREPARACAO_APROVADA: tudo pronto para executar o comando 'compilar'."
}

if [[ "$COMMAND" == "preparar" ]]; then
  prepare
  exit 0
fi

if (( $# != 1 )); then
  usage
  exit 2
fi
ROM_INPUT="$1"
if [[ ! -f "$ROM_INPUT" ]]; then
  echo "ERRO: ROM nao encontrada: $ROM_INPUT" >&2
  exit 3
fi
ROM_INPUT="$(realpath "$ROM_INPUT")"
ROM_ACTUAL="$(sha256sum "$ROM_INPUT" | awk '{print $1}')"
if [[ "$ROM_ACTUAL" != "$ROM_SHA256" ]]; then
  echo "ERRO: ROM nao e a versao USA original esperada." >&2
  echo "SHA256 calculado: $ROM_ACTUAL" >&2
  echo "SHA256 esperado: $ROM_SHA256" >&2
  exit 3
fi
command -v docker >/dev/null || { echo "Docker nao encontrado; execute preparar." >&2; exit 3; }
command -v cargo >/dev/null || { [[ -f "$HOME/.cargo/env" ]] && source "$HOME/.cargo/env"; }
command -v cargo >/dev/null || { echo "Rust nao encontrado; execute preparar." >&2; exit 3; }

WORKDIR="$HOME/SMWRecomp-R36S-Local"
if [[ -n "$SMW_WORKDIR" ]]; then WORKDIR="$SMW_WORKDIR"; fi
mkdir -p "$WORKDIR" "$WORKDIR/logs" "$WORKDIR/saida"
WORKDIR="$(realpath "$WORKDIR")"
SOURCE="$WORKDIR/SuperMarioWorldRecomp"
PORT="$WORKDIR/smw-port"
KIT="$WORKDIR/kit"
OUT="$WORKDIR/saida"

echo "ROM validada. Trabalhando em: $WORKDIR"
echo "O executavel R36S e a ROM nao serao enviados ao GitHub."

if [[ ! -d "$PORT/.git" ]]; then
  git clone --depth 1 "$PORT_REPO" "$PORT"
else
  git -C "$PORT" pull --ff-only
fi

if [[ ! -d "$SOURCE/.git" ]]; then
  git clone --recurse-submodules "$SOURCE_REPO" "$SOURCE"
  git -C "$SOURCE" checkout --detach "$SOURCE_REVISION"
  git -C "$SOURCE" submodule update --init --recursive
else
  CURRENT_REVISION="$(git -C "$SOURCE" rev-parse HEAD)"
  if [[ "$CURRENT_REVISION" != "$SOURCE_REVISION" ]]; then
    echo "ERRO: checkout local tem revisao inesperada $CURRENT_REVISION" >&2
    echo "Use outro SMW_WORKDIR para nao sobrescrever suas alteracoes." >&2
    exit 4
  fi
  git -C "$SOURCE" submodule update --init --recursive
fi

if [[ ! -f "$SOURCE/src/port/gles2_renderer.c" ]]; then
  echo "Aplicando port SDL2/OpenGL ES2 ao checkout separado..."
  mkdir -p "$KIT"
  base64 --decode "$PORT/cloud-kit/EmuELEC48_Kit.tar.xz.b64" > "$WORKDIR/EmuELEC48_Kit.tar.xz"
  echo "$KIT_SHA256  $WORKDIR/EmuELEC48_Kit.tar.xz" | sha256sum --check
  tar -xJf "$WORKDIR/EmuELEC48_Kit.tar.xz" -C "$KIT"
  cp -a "$KIT/tools/." "$SOURCE/tools/"
  cp -a "$KIT/ports" "$SOURCE/"
  (
    cd "$SOURCE"
    python3 tools/apply_emuelec.py
    python3 - <<'PY'
from pathlib import Path
p = Path("src/port/gles2_renderer.c")
s = p.read_text()
marker = "&renderer_begin_draw, &renderer_end_draw,"
if s.count(marker) != 1:
    raise SystemExit("Erro: vtable GLES2 alterada na base original")
p.write_text(s.replace(marker, marker + "\n      NULL,", 1))
PY
    grep -q EMUELEC_GLES2_PORT CMakeLists.txt
  )
fi

if [[ -e "$SOURCE/smw.sfc" ]]; then
  echo "ERRO: ja existe uma ROM no checkout local; nao vou sobrescreve-la." >&2
  exit 4
fi
cleanup() {
  rm -f "$SOURCE/smw.sfc"
}
trap cleanup EXIT

# Regenerate only on first build unless explicit FORCAR_REGEN=1.
REGENERATE=0
if ! compgen -G "$SOURCE/src/gen/*.c" >/dev/null; then REGENERATE=1; fi
if [[ "$FORCAR_REGEN" == "1" ]]; then REGENERATE=1; fi
if (( REGENERATE == 1 )); then
  echo "Gerando codigo C da CPU 65816 (host local)..."
  umask 077
  cp "$ROM_INPUT" "$SOURCE/smw.sfc"
  (
    cd "$SOURCE"
    export SNESRECOMP_ANALYSIS_BACKEND=native
    bash tools/regen.sh --stock --no-tests
  ) 2>&1 | tee "$WORKDIR/logs/01-geracao-c.txt"
  rm -f "$SOURCE/smw.sfc"
else
  echo "Codigo C src/gen encontrado; reutilizando arquivos gerados."
fi

if [[ -e "$SOURCE/smw.sfc" ]]; then
  echo "Falha de seguranca: ROM ainda existe no checkout; abortando." >&2
  exit 5
fi

echo "Construindo imagem ARM64 com Debian Buster / GLIBC 2.28..."
sudo docker build --platform linux/arm64 \
  --file "$PORT/cloud-kit/r36s/Dockerfile.buster-arm64" \
  --tag smw-r36s-buster:local \
  "$PORT/cloud-kit/r36s" 2>&1 | tee "$WORKDIR/logs/02-docker-buster.txt"

sudo docker run --rm --platform linux/arm64 smw-r36s-buster:local \
  sh -c 'test "$(uname -m)" = aarch64 && test "$(getconf GNU_LIBC_VERSION)" = "glibc 2.28"'

if [[ "$JOBS" =~ ^[1-9][0-9]*$ ]]; then
  PARALLEL="$JOBS"
else
  PARALLEL=2
fi

echo "Compilando executavel ARM64 e montando pacote R36S..."
sudo docker run --rm --platform linux/arm64 \
  --mount "type=bind,src=$SOURCE,dst=/src" \
  --mount "type=bind,src=$PORT,dst=/port-code,readonly" \
  --mount "type=bind,src=$OUT,dst=/output" \
  --env "JOBS=$PARALLEL" \
  smw-r36s-buster:local \
  bash /port-code/cloud-kit/r36s/build-and-package.sh \
  /src /port-code /output 2>&1 | tee "$WORKDIR/logs/03-compilacao-r36s.txt"

test -f "$OUT/smwrecompr36s/SuperMarioWorldSNESRecomp"
test -f "$OUT/SMW Recomp R36S.sh"
grep -q "PASS R36S_PORTMASTER_PACKAGE" "$WORKDIR/logs/03-compilacao-r36s.txt"

if find "$OUT" -type f \( -iname '*.sfc' -o -iname '*.smc' \) | grep -q .; then
  echo "ERRO: ROM encontrada no pacote; nao comprimindo." >&2
  exit 6
fi

FINAL_ZIP="$WORKDIR/SMWRecomp-R36S-ARM64-GLES2-GLIBC228.zip"
(
  cd "$OUT"
  zip -qr -FS "$FINAL_ZIP" .
)
echo
echo "BUILD_R36S_LOCAL_PASS"
echo "Pacote para SD: $FINAL_ZIP"
echo "Dados e launcher: $OUT/"
echo "Logs: $WORKDIR/logs/"
echo "Apenas candidato experimental. SDL2/EGL/GLES, gamepad e desempenho dependem de teste real."
