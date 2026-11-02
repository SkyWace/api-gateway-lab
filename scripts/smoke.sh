#!/usr/bin/env bash
# Smoke tests fonctionnels + sécurité (routage, auth, CORS, en-têtes, requêtes malformées).
# Usage : ./scripts/smoke.sh kong     -> sortie lisible + log dans results/<gw>-smoke-<date>.log
set -uo pipefail
source "$(dirname "$0")/env.sh"
GW=${1:?usage: smoke.sh kong|apisix|traefik|scg}
BASE=$(gw_url "$GW")
LOG="results/${GW}-smoke-$(date +%Y%m%d-%H%M%S).log"
mkdir -p results
TOKEN=$(get_token)
pass=0; fail=0

t() { # t "<nom>" <regex code attendu> curl-args...  (un KO est une OBSERVATION à analyser, pas forcément un bug)
  local name=$1 expected=$2; shift 2
  local code; code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@")
  if [[ "$code" =~ ^($expected)$ ]]; then echo "OK  [${code}] ${name}"; ((pass++)); else echo "KO  [${code} au lieu de ${expected}] ${name}"; ((fail++)); fi
}

{
echo "=== Smoke $GW ($BASE) — $(date -Iseconds)"
echo "--- Routage"
t "GET /api/catalog -> catalog"            200 "$BASE/api/catalog"
t "GET /api/catalog/7"                      200 "$BASE/api/catalog/7"
t "GET /api/catalog/999 (404 backend)"      404 "$BASE/api/catalog/999"
t "Route inconnue /api/unknown"             404 "$BASE/api/unknown"
t "/admin/chaos non exposé par la gateway"  404 "$BASE/admin/chaos"
echo "--- Authentification"
t "orders sans token"                       401 "$BASE/api/orders/1"
t "orders avec token"                       200 -H "Authorization: Bearer $TOKEN" "$BASE/api/orders/1"
t "POST orders avec token"                  201 -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"sku":"SKU-1001","qty":3}' "$BASE/api/orders"
echo "--- CORS"
t "Préflight origine autorisée"             "200|204" -X OPTIONS -H 'Origin: http://localhost:5173' -H 'Access-Control-Request-Method: GET' "$BASE/api/catalog"
echo "    En-têtes CORS origine autorisée :"
curl -s -D - -o /dev/null -X OPTIONS -H 'Origin: http://localhost:5173' -H 'Access-Control-Request-Method: GET' "$BASE/api/catalog" | grep -i '^access-control' | sed 's/^/      /'
echo "    En-têtes CORS origine NON autorisée (attendu : pas d'Access-Control-Allow-Origin) :"
curl -s -D - -o /dev/null -X OPTIONS -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: GET' "$BASE/api/catalog" | grep -i '^access-control-allow-origin' | sed 's/^/      /' || echo "      (aucun) -> OK"
echo "--- Requêtes malformées"
t "Path traversal /api/catalog/../orders/1 (normalisé -> 401 attendu)" 401 --path-as-is "$BASE/api/catalog/../orders/1"
t "JSON invalide sur POST orders"           400 -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{bad' "$BASE/api/orders"
t "Header géant (16 Ko) rejeté (4xx)"         "4[0-9][0-9]" -H "X-Big: $(head -c 16384 /dev/zero | tr '\0' a)" "$BASE/api/catalog/1"
t "Méthode non prévue (DELETE)"             405 -X DELETE "$BASE/api/catalog/1"
echo "--- En-têtes de réponse (fuite d'info, corrélation)"
curl -s -D - -o /dev/null "$BASE/api/catalog/1" | grep -iE '^(server|via|x-powered-by|x-request-id|x-instance|x-ratelimit|ratelimit|x-kong)' | sed 's/^/      /'
echo "=== $pass OK / $fail KO"
} | tee "$LOG"
echo "Log : $LOG"
