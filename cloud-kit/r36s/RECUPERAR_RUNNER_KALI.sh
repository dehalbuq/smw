#!/usr/bin/env bash
# Recover a GitHub Actions self-hosted runner deleted server-side.
# Scope: one isolated Kali VM and one private repository only.
# Run as smwrunner, NOT root. Never send authorization codes/tokens to a chat.
set -Eeuo pipefail
REPO="dehalbuq/smw-rom-private"
RUNNER_NAME="kali-r36s-kali"
RUNNER_LABEL="r36s-kali"
RUNNER_DIR="/home/smwrunner/actions-runner-smw-r36s"

fail() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }
[[ "$(id -un)" == "smwrunner" ]] || fail "Execute no terminal como smwrunner (su - smwrunner)"
[[ -d "$RUNNER_DIR" && -f "$RUNNER_DIR/config.sh" && -f "$RUNNER_DIR/svc.sh" ]] \
  || fail "Instalacao runner nao encontrada em $RUNNER_DIR"
command -v gh >/dev/null || fail "GitHub CLI gh nao esta instalado"
command -v sudo >/dev/null || fail "sudo nao esta instalado"
cd "$RUNNER_DIR"

printf '== 1. Parar e desinstalar SOMENTE o servico do runner ==\n'
sudo ./svc.sh stop || true
sudo ./svc.sh uninstall || true

printf '== 2. Guardar configuracao ANTIGA no home privado ==\n'
BACKUP_ROOT="$HOME/.r36s-runner-registration-backups"
mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"
BACKUP="$BACKUP_ROOT/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -m 700 "$BACKUP"
for item in .runner .credentials .credentials_rsaparams; do
  if [[ -e "$item" ]]; then
    mv -- "$item" "$BACKUP/$item"
  fi
done
echo "Cadastro local anterior guardado em pasta com permissao restrita."
echo "Nao apagamos a VM, Docker, codigo, cache nem pasta _work."

printf '== 3. Autorizar conta GitHub temporariamente ==\n'
# Avoid leaving an administrator's gh CLI session accessible to runner jobs.
GH_CONFIG_DIR="$(mktemp -d "$HOME/.gh-runner-recovery.XXXXXX")"
chmod 700 "$GH_CONFIG_DIR"
export GH_CONFIG_DIR
cleanup() {
  rm -rf -- "$GH_CONFIG_DIR"
}
trap cleanup EXIT
echo "Use a autorizacao no navegador. Nao cole senha/token neste chat."
gh auth login --hostname github.com --web --git-protocol https --scopes repo --insecure-storage
gh api "repos/$REPO" --jq '.full_name' | grep -Fx "$REPO" >/dev/null \
  || fail "A conta autorizada nao tem acesso ao repositorio"

printf '== 4. Registrar NOVA identidade do runner no repo privado ==\n'
REG_TOKEN="$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq '.token')"
[[ -n "$REG_TOKEN" && "$REG_TOKEN" != "null" ]] || fail "Falha ao obter token de registro"
./config.sh --unattended \
  --url "https://github.com/$REPO" \
  --token "$REG_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABEL" \
  --work "_work" \
  --replace
unset REG_TOKEN
echo "Re-registro concluido."

printf '== 5. Instalar e iniciar servico novamente ==\n'
sudo ./svc.sh install smwrunner
sudo ./svc.sh start
sleep 4
sudo ./svc.sh status

printf '== 6. Conferir registro ONLINE no GitHub ==\n'
ONLINE=0
for _ in 1 2 3 4 5; do
  STATE="$(gh api "repos/$REPO/actions/runners?per_page=100" \
    --jq ".runners[] | select(.name == \"$RUNNER_NAME\") | .status" \
    | head -1 || true)"
  echo "Runner $RUNNER_NAME: ${STATE:-nao-encontrado}"
  if [[ "$STATE" == "online" ]]; then
    ONLINE=1
    break
  fi
  sleep 4
done
if [[ "$ONLINE" != 1 ]]; then
  echo "Runner ainda nao esta ONLINE. Verifique o log systemd."
  sudo journalctl --no-pager -n 40 \
    -u "actions.runner.dehalbuq-smw-rom-private.$RUNNER_NAME.service" || true
  fail "Cadastro refeito mas runner nao foi confirmado online."
fi
echo "RUNNER_KALI_RECADASTRADO_ONLINE=PASS"
echo "Workflow: https://github.com/dehalbuq/smw-rom-private/actions/runs/43343110703"
