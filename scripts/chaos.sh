#!/usr/bin/env bash
# Pannes à injecter PENDANT resilience.js. Usage : ./scripts/chaos.sh <scenario>
#   kill-catalog2   : stoppe catalog-2 (failover attendu vers catalog-1), relance après 30 s
#   kill-orders     : stoppe orders 30 s (seule instance : 502/503 attendus, CB selon gateway)
#   errors-orders   : 50 % d'erreurs 500 sur orders pendant 30 s
#   slow-orders     : latence de 7 s sur orders pendant 30 s (> timeout de 5 s)
#   reset           : remet tout à zéro
set -euo pipefail
cd "$(dirname "$0")/.."
log() { echo "$(date +%H:%M:%S.%3N) $*" | tee -a results/chaos-events.log; }
mkdir -p results
case "${1:?scenario}" in
  kill-catalog2) log "STOP catalog-2"; docker compose stop catalog-2; sleep 30; log "START catalog-2"; docker compose start catalog-2 ;;
  kill-orders)   log "STOP orders";    docker compose stop orders;    sleep 30; log "START orders";    docker compose start orders ;;
  errors-orders) log "orders error=0.5"; curl -s "http://localhost:9003/admin/chaos?error=0.5" >/dev/null; sleep 30; curl -s "http://localhost:9003/admin/chaos?error=0" >/dev/null; log "orders error=0" ;;
  slow-orders)   log "orders delay=7000"; curl -s "http://localhost:9003/admin/chaos?delay=7000" >/dev/null; sleep 30; curl -s "http://localhost:9003/admin/chaos?delay=0" >/dev/null; log "orders delay=0" ;;
  reset) for p in 9001 9002 9003; do curl -s "http://localhost:$p/admin/chaos?delay=0&error=0" >/dev/null || true; done; docker compose start catalog-1 catalog-2 orders; log "reset" ;;
  *) echo "scénario inconnu"; exit 1 ;;
esac
