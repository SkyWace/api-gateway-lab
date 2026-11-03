#!/usr/bin/env bash
# Lance TOUTES les expériences E1 → E8 sur une gateway, sans intervention (Linux).
# Les étapes "deux terminaux" (stats, pannes, reload) tournent en arrière-plan automatiquement.
#
#   ./scripts/run-all.sh kong          (≈ 25 min)   — aussi : apisix
#   SKIP_BASELINE=1 ./scripts/run-all.sh kong       — ne refait pas la baseline "direct"
#
# Tout est écrit dans results/ ; un résumé est affiché à la fin.
set -uo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh

GW=${1:-kong}
BASE=$(gw_url "$GW") || exit 1
mkdir -p results
LOG="results/${GW}-run-all-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 manquant : sudo apt install docker-compose-v2"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker inaccessible : sudo usermod -aG docker \$USER puis reconnecte-toi"; exit 1; }

step() { echo; echo "=================== $* ($(date +%H:%M:%S))"; }
k6run() { docker compose --profile tools run --rm k6 run "$@"; }
wait_http() { # wait_http <url> <code attendu> <timeout s>
  local i; for ((i = 0; i < $3; i += 2)); do
    [[ "$(curl -s -o /dev/null -w '%{http_code}' "$1")" == "$2" ]] && return 0; sleep 2; done
  echo "!! $1 ne répond pas $2 après $3 s"; return 1; }
gw_ready() { wait_http "$BASE/api/catalog/1" 200 120; }

# ------------------------------------------------------------------ démarrage
step "Démarrage $GW"
docker compose --profile "$GW" up -d --build
wait_http "$KEYCLOAK/realms/lab" 200 180 || exit 1
gw_ready || exit 1
./scripts/check-limits.sh

# ------------------------------------------------------------------ E1 + E7
step "E1/E7 — smoke"
./scripts/smoke.sh "$GW"

# ------------------------------------------------------------------ E2
step "E2 — authentification"
k6run /scripts/auth.js -e TARGET="$GW" 2>&1 | tee "results/${GW}-auth.log"

# ------------------------------------------------------------------ E3
step "E3 — rate limiting"
k6run /scripts/ratelimit.js -e TARGET="$GW" 2>&1 | tee "results/${GW}-ratelimit.log"

# ------------------------------------------------------------------ E4 latence
if [[ -z "${SKIP_BASELINE:-}" ]]; then
  step "E4 — baseline directe (3 × 60 s)"
  for i in 1 2 3; do k6run /scripts/latency.js -e TARGET=direct 2>&1 | tee "results/direct-latency-$i.log"; done
fi
step "E4 — latence $GW (échauffement + 3 × 60 s + orders)"
k6run /scripts/latency.js -e TARGET="$GW" -e DURATION=30s >/dev/null 2>&1
for i in 1 2 3; do k6run /scripts/latency.js -e TARGET="$GW" 2>&1 | tee "results/${GW}-latency-$i.log"; done
k6run /scripts/latency.js -e TARGET="$GW" -e ENDPOINT=orders 2>&1 | tee "results/${GW}-latency-orders.log"

# ------------------------------------------------------------------ E4 débit
step "E4 — débit (stats CPU/RAM en arrière-plan)"
./scripts/stats.sh "$GW" > /dev/null 2>&1 & STATS=$!
k6run /scripts/throughput.js -e TARGET="$GW" 2>&1 | tee "results/${GW}-throughput.log"
kill "$STATS" 2>/dev/null; wait "$STATS" 2>/dev/null

# ------------------------------------------------------------------ E5
step "E5 — répartition"
k6run /scripts/loadbalancing.js -e TARGET="$GW" 2>&1 | tee "results/${GW}-lb.log"

for sc in kill-catalog2:catalog errors-orders:orders slow-orders:orders kill-orders:orders; do
  name=${sc%%:*}; ep=${sc##*:}
  step "E5 — $name (panne injectée à t+20 s)"
  ( sleep 20; ./scripts/chaos.sh "$name" > /dev/null 2>&1 ) & CHAOS=$!
  k6run /scripts/resilience.js -e TARGET="$GW" -e ENDPOINT="$ep" 2>&1 | tee "results/${GW}-${name}.log"
  wait "$CHAOS" 2>/dev/null
  ./scripts/chaos.sh reset > /dev/null 2>&1   # backends à zéro + redémarrage de la gateway
  gw_ready
done

# ------------------------------------------------------------------ E6
step "E6 — observabilité"
{
  echo "--- En-têtes de corrélation"
  curl -si "$BASE/api/catalog/1" | grep -iE "x-request-id|x-kong|server"
  echo "--- ID client conservé et vu par le backend"
  curl -s -H 'X-Request-ID: test-123' "$BASE/api/catalog/1" | grep -o '"headersSeen":{[^}]*}'
  echo "--- ID dans les logs de la gateway"
  docker compose --profile "$GW" logs "$GW" 2>/dev/null | grep -c test-123 | sed 's/^/occurrences : /'
  echo "--- Métriques Prometheus exposées par la gateway"
  case "$GW" in
    kong)   curl -s http://localhost:18100/metrics | grep -E "^kong_(http_requests_total|request_latency_ms_count)" | head -10 ;;
    apisix) curl -s http://localhost:19091/apisix/prometheus/metrics | grep -E "^apisix_(http_status|http_latency_count)" | head -10 ;;
  esac
} 2>&1 | tee "results/${GW}-observabilite.log"
docker compose --profile obs up -d prometheus > /dev/null 2>&1 && sleep 15
q="sum(${GW}_http_requests_total)%20by%20(code)"; [[ $GW == apisix ]] && q="sum(apisix_http_status)%20by%20(code)"
curl -s "http://localhost:9090/api/v1/query?query=$q" | tee -a "results/${GW}-observabilite.log"; echo

# ------------------------------------------------------------------ E8
step "E8 — changement de route à chaud (trafic continu en parallèle)"
k6run /scripts/latency.js -e TARGET="$GW" -e RATE=50 -e DURATION=60s > "results/${GW}-reload-traffic.log" 2>&1 & TRAFFIC=$!
sleep 15
./scripts/reload.sh "$GW" 2>&1 | tee "results/${GW}-reload.log"
wait "$TRAFFIC"
grep -E "http_req_failed|checks" "results/${GW}-reload-traffic.log" | tee -a "results/${GW}-reload.log"
case "$GW" in   # restauration de la configuration d'origine
  apisix) [[ -f gateways/apisix/apisix.yaml.bak ]] && cat gateways/apisix/apisix.yaml.bak > gateways/apisix/apisix.yaml ;;
esac
docker compose --profile "$GW" restart "$GW" > /dev/null 2>&1 && gw_ready

# ------------------------------------------------------------------ fin
step "Fin — journaux et graphiques"
docker compose --profile "$GW" logs "$GW" > "results/${GW}-gateway.log" 2>&1
python3 scripts/graphs.py || echo "(graphiques : installer python3-matplotlib)"

echo; echo "=================== RÉSUMÉ $GW"
grep -hE "^=== [0-9]+ OK" "$(ls -t results/${GW}-smoke-*.log | head -1)"
echo "Auth : $(grep -c '^time=.*OK ' "results/${GW}-auth.log")/9 OK"
grep -hE "client:client" "results/${GW}-ratelimit.log"
grep -HE "http_req_duration\." results/${GW}-latency-*.log
grep -E "palier:" "results/${GW}-throughput.log" | head -5
grep -hE "instance:catalog" "results/${GW}-lb.log"
for n in kill-catalog2 errors-orders slow-orders kill-orders; do echo "-- $n"; grep -hE "status:(200|500|502|503|504)" "results/${GW}-$n.log" | grep -v ": 0 "; done
grep -E "Route active|non prise" "results/${GW}-reload.log"
echo; echo "Journal complet : $LOG"
echo "Puis : git add results docs/graphs && git commit -m \"Résultats $GW\" && git push"
