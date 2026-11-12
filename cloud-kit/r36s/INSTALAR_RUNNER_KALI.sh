#!/usr/bin/env bash
# Setup one GitHub Actions self-hosted runner within the Kali VirtualBox VM.
# ONLY for the user's private dehalbuq/smw-rom-private repository.
# Run as an unprivileged interactive user, NOT root.
set -Eeuo pipefail
REPO="dehalbuq/smw-rom-private"
LABEL="r36s-kali"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-smw-r36s}"
RUNNER_NAME="${RUNNER_NAME:-kali-r36s-$(hostname -s)}"

fail() { echo "ERRO: $*" >&2; exit 1; }
[[ "$EUID" -ne 0 ]] || fail "Nao execute como root; use seu usuario Kali."
[[ "$(uname -s)" == Linux ]] || fail "Somente Linux."
[[ "$(uname -m)" == x86_64 ]] || fail "Este instalador visa Kali x86_64 na VirtualBox."
command -v sudo >/dev/null || fail "sudo nao encontrado."
command -v apt-get >/dev/null || fail "apt-get nao encontrado; execute no Kali Linux."

echo "== Kali R36S: preparando dependencias =="
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl jq tar unzip zip git python3 python3-pip \
  gcc g++ build-essential pkg-config cmake ninja-build file binutils xz-utils \
  docker.io qemu-user-static binfmt-support gh libicu-dev libssl-dev
sudo systemctl enable --now docker
if command -v update-binfmts >/dev/null 2>&1; then
  sudo update-binfmts --enable qemu-aarch64 || true
fi
if ! id -nG | grep -qw docker; then
  echo "Adicionando usuario $(id -un) ao grupo docker; permissao elevada DENTRO DA VM."
  sudo usermod -aG docker "$(id -un)"
fi
sudo docker info >/dev/null || fail "Docker daemon inacessivel com sudo."
if ! sudo docker run --rm --platform linux/arm64 debian:buster \
    sh -c 'test "$(uname -m)" = aarch64'; then
  fail "QEMU ARM64 nao funciona. Verifique binfmt e VirtualBox."
fi
echo "PASS Docker/QEMU ARM64"
if ! command -v rustup >/dev/null 2>&1; then
  echo "Instalando Rust oficial no usuario da VM"
  RUSTUP_SH="$(mktemp)"
  curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs -o "$RUSTUP_SH"
  sh "$RUSTUP_SH" -y --profile minimal --default-toolchain stable
  rm -f "$RUSTUP_SH"
fi
if [[ -f "$HOME/.cargo/env" ]]; then
  source "$HOME/.cargo/env"
fi
rustup toolchain install stable --profile minimal
command -v cargo >/dev/null || fail "cargo/rustc indisponiveis"

echo
echo "== Autorizar GitHub na VM (somente para registrar o runner) =="
# NUNCA manter uma credencial gh permanente no usuario que executara workflows.
# A sessao gh sera armazenada sem keyring em pasta temporaria, eliminada na saida.
GH_CONFIG_DIR="$(mktemp -d)"
chmod 700 "$GH_CONFIG_DIR"
export GH_CONFIG_DIR
trap 'rm -rf "$GH_CONFIG_DIR"' EXIT
echo "Complete a autorizacao pelo navegador. Nao envie token ou senha para o chat."
gh auth login --hostname github.com --web --git-protocol https --scopes "repo" --insecure-storage
gh api "repos/$REPO" --jq '.full_name' | grep -Fx "$REPO" >/dev/null \
  || fail "Conta gh sem acesso ao repositorio privado"

echo
echo "== Instalando runner oficial GitHub Linux x64 =="
mkdir -p "$RUNNER_DIR"
if [[ -f "$RUNNER_DIR/.runner" ]]; then
  echo "Runner ja registrado: $RUNNER_DIR"
  sudo "$RUNNER_DIR/svc.sh" status || true
  exit 0
fi

RELEASE_JSON="$(mktemp)"
curl -fsSL --retry 3 https://api.github.com/repos/actions/runner/releases/latest -o "$RELEASE_JSON"
mapfile -t RELEASE < <(python3 - "$RELEASE_JSON" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
assets = [a for a in r["assets"]
          if a["name"].startswith("actions-runner-linux-x64-")
          and a["name"].endswith(".tar.gz")]
if len(assets) != 1:
    raise SystemExit("Nao foi identificado um pacote Linux x64 unico.")
a = assets[0]
print(a["browser_download_url"])
print(a.get("digest") or "")
print(a["name"])
PY
)
rm -f "$RELEASE_JSON"
ASSET_URL="${RELEASE[0]}"
ASSET_DIGEST="${RELEASE[1]}"
ARCHIVE="$(mktemp --suffix=.tar.gz)"
curl -fL --retry 3 "$ASSET_URL" -o "$ARCHIVE"
if [[ "$ASSET_DIGEST" == sha256:* ]]; then
  echo "${ASSET_DIGEST#sha256:}  $ARCHIVE" | sha256sum -c -
else
  echo "Release nao forneceu digest SHA256. Verifique GitHub release manualmente."
  fail "Cancelado por seguranca: download sem checksum"
fi
tar -xzf "$ARCHIVE" -C "$RUNNER_DIR"
rm -f "$ARCHIVE"
cd "$RUNNER_DIR"

echo "== Registrando runner no repo PRIVADO =="
REGISTRATION_TOKEN="$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq '.token')"
[[ -n "$REGISTRATION_TOKEN" ]] || fail "Falha ao obter token de registro"
./config.sh --unattended \
  --url "https://github.com/$REPO" \
  --token "$REGISTRATION_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$LABEL" \
  --work "_work" \
  --replace
unset REGISTRATION_TOKEN
rm -rf "$GH_CONFIG_DIR"
unset GH_CONFIG_DIR

echo "== Habilitando servico na VM =="
sudo ./svc.sh install "$(id -un)"
sudo ./svc.sh start
sudo ./svc.sh status
echo
echo "RUNNER_KALI_INSTALADO=PASS"
echo "Runner: $RUNNER_NAME"
echo "Repo: https://github.com/$REPO/settings/actions/runners"
echo "Label: $LABEL"
echo "NUNCA monte pastas privadas do Windows na VM de compilacao."
