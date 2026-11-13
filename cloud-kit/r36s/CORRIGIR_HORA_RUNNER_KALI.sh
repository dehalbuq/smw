#!/usr/bin/env bash
# Diagnose and repair clock skew that can masquerade as "runner registration deleted".
# Runs inside the isolated Kali VM. Never edits .runner/.credentials or the Windows host.
set -Eeuo pipefail
RUNNER_DIR="/home/smwrunner/actions-runner-smw-r36s"
SERVICE="actions.runner.dehalbuq-smw-rom-private.kali-r36s-kali.service"
MAX_DRIFT=30

fail(){ echo "ERRO: $*" >&2; exit 1; }
[[ "$(id -un)" == smwrunner ]] || fail "Execute como smwrunner, nao como root."
command -v sudo >/dev/null || fail "sudo indisponivel"
command -v curl >/dev/null || fail "curl indisponivel"
[[ -x "$RUNNER_DIR/svc.sh" ]] || fail "Runner nao existe em $RUNNER_DIR"

server_epoch() {
  local headers server_date
  headers="$(curl -sSLI --connect-timeout 7 --max-time 20 --retry 2 \
    -H 'Cache-Control: no-cache' https://api.github.com/)" \
    || fail "Nao foi possivel obter data via HTTPS do GitHub."
  server_date="$(printf '%s\n' "$headers" | awk 'tolower($1)=="date:" {
    sub(/\r$/, "", $0); sub(/^[^:]*:[[:space:]]*/, "", $0); v=$0;
  } END {print v}')"
  [[ -n "$server_date" ]] || fail "Cabecalho Date nao encontrado no HTTPS do GitHub."
  date -u -d "$server_date" +%s || fail "Data do GitHub nao foi reconhecida."
}
measure_drift() {
  local local_epoch remote_epoch
  local_epoch="$(date -u +%s)"
  remote_epoch="$(server_epoch)"
  DIFF="$((local_epoch - remote_epoch))"
  ABS="$DIFF"
  (( ABS >= 0 )) || ABS="$((-ABS))"
  echo "TIME_DRIFT_SECONDS=$DIFF"
  echo "TIME_DRIFT_ABS_SECONDS=$ABS"
}

echo "== Horario UTC do Kali =="
date -u '+KALI_UTC=%Y-%m-%dT%H:%M:%SZ'
echo "== Sincronizacao atual =="
timedatectl status --no-pager || true
measure_drift

if (( ABS > MAX_DRIFT )); then
  echo "CLOCK_SKEW_DETECTED=YES"
  echo "Sincronizando relogio da VM via NTP; nenhuma credencial GitHub sera alterada."
  sudo timedatectl set-ntp true || true
  if command -v chronyc >/dev/null 2>&1; then
    sudo systemctl enable --now chrony || true
    sudo chronyc -a makestep || true
  elif systemctl list-unit-files systemd-timesyncd.service --no-legend 2>/dev/null | grep -q systemd-timesyncd; then
    sudo systemctl restart systemd-timesyncd || true
  fi
  sleep 6
  measure_drift
  if (( ABS > MAX_DRIFT )); then
    echo "NTP nao ajustou o relogio. Tentando chrony do Kali..."
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y chrony
    sudo systemctl enable --now chrony
    sudo chronyc -a makestep || true
    sleep 7
    measure_drift
  fi
  if (( ABS > MAX_DRIFT )); then
    echo "CLOCK_SKEW_NOT_FIXED=YES"
    echo "Confira o relogio do Windows host e o Guest Additions da VirtualBox."
    fail "Diferenca de tempo ainda acima de $MAX_DRIFT segundos; nao reiniciaremos o runner com token invalido."
  fi
  echo "CLOCK_SKEW_FIXED=PASS"
else
  echo "CLOCK_SKEW_DETECTED=NO"
fi

echo "== Reiniciando somente o servico runner existente =="
sudo systemctl restart "$SERVICE"
sleep 10
if sudo systemctl is-active --quiet "$SERVICE"; then
  echo "RUNNER_SYSTEMD_ACTIVE=PASS"
else
  echo "RUNNER_SYSTEMD_ACTIVE=FAIL"
fi

echo "== Estado resumido do listener (sem credenciais) =="
JOURNAL="$(sudo journalctl --no-pager --since '35 seconds ago' -u "$SERVICE" \
  -o cat 2>/dev/null || true)"
printf '%s\n' "$JOURNAL" |
  grep -E 'Connected to GitHub|Listening for Jobs|Running job:|Failed to create a session|Runner listener exited' \
  | tail -12 || true

if sudo systemctl is-active --quiet "$SERVICE" && \
   printf '%s\n' "$JOURNAL" | grep -Eq 'Listening for Jobs|Running job:'; then
  echo "RUNNER_KALI_ONLINE=PASS"
  echo "WORKFLOW=https://github.com/dehalbuq/smw-rom-private/actions/runs/43343110703"
else
  echo "RUNNER_KALI_ONLINE=NOT_CONFIRMED"
  latest_diag="$(find "$RUNNER_DIR/_diag" -maxdepth 1 -type f -name 'Runner_*.log' \
    -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2- || true)"
  if [[ -n "$latest_diag" ]]; then
    grep -qi 'token expired' "$latest_diag" && echo "DIAG_EXPIRED_TOKEN=YES" || true
    grep -qi 'Current server time' "$latest_diag" && echo "DIAG_SERVER_CLOCK_MENTIONED=YES" || true
    grep -qi 'VssOAuthTokenRequestException' "$latest_diag" && echo "DIAG_OAUTH_ERROR=YES" || true
  fi
  echo "Se continuar offline, envie apenas estas linhas RESUMIDAS e a saida de timedatectl status."
  exit 2
fi
