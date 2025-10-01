#!/usr/bin/env bash
# Simple service monitor with health check, restart attempts, flock, and syslog logging.
set -euo pipefail

SERVICE="${1:-nginx}"            # pass a service name, defaults to nginx
LOCKFILE="${XDG_RUNTIME_DIR:-/tmp}/monitor_${SERVICE}.lock"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/}"  # override via env if desired
RETRIES="${RETRIES:-2}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-5}"

exec 9>"$LOCKFILE" || exit 1
flock -n 9 || { echo "Another instance is running"; exit 0; }

log(){ logger -t "monitor_${SERVICE}" "$*"; echo "$(date -Is) $*"; }

if systemctl is-active --quiet "$SERVICE"; then
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null; then
      log "$SERVICE healthy"
      exit 0
    else
      log "$SERVICE up but health check failed"
    fi
  else
    log "$SERVICE active (no curl for health check)"
    exit 0
  fi
else
  log "$SERVICE inactive"
fi

# Optional service-specific config test (nginx example)
if [[ "$SERVICE" == "nginx" ]] && command -v nginx >/dev/null 2>&1; then
  if ! nginx -t >/dev/null 2>&1; then
    log "Config test FAILED; refusing to restart $SERVICE"
    exit 1
  fi
fi

for i in $(seq 1 "$RETRIES"); do
  log "Attempting to restart $SERVICE (try $i/$RETRIES)"
  if sudo systemctl restart "$SERVICE"; then
    sleep "$SLEEP_BETWEEN"
    if systemctl is-active --quiet "$SERVICE"; then
      if command -v curl >/dev/null 2>&1 && ! curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null; then
        log "$SERVICE restarted but health check failed"
        continue
      fi
      log "$SERVICE restarted and healthy"
      exit 0
    fi
  fi
done

log "FAILED to restore $SERVICE after $RETRIES attempt(s)"
exit 1
