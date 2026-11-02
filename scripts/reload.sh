#!/usr/bin/env bash
# Expérience DÉPLOIEMENT À CHAUD : ajoute une route /api/v2/catalog SANS redémarrage,
# pendant qu'un trafic tourne (lancer latency.js à côté), et mesure le délai de prise en compte.
# Usage : ./scripts/reload.sh kong|apisix|traefik|scg
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
GW=${1:?gateway}
BASE=$(gw_url "$GW")
start=$(now_ms)
case "$GW" in
  kong)
    # DB-less : on pousse le fichier déclaratif complet via l'Admin API
    sed 's#paths: \["/api/catalog"\]#paths: ["/api/catalog", "/api/v2/catalog"]#' gateways/kong/kong.yml > /tmp/kong-v2.yml
    curl -s -o /dev/null -w "POST /config -> %{http_code}\n" -X POST http://localhost:18001/config -F config=@/tmp/kong-v2.yml ;;
  apisix)
    # Standalone : APISIX relit apisix.yaml automatiquement
    # Fichier monté seul : on réécrit EN PLACE (même inode) sinon le conteneur garde l'ancienne version
    cp gateways/apisix/apisix.yaml gateways/apisix/apisix.yaml.bak
    sed 's#uris: \["/api/catalog", "/api/catalog/\*"\]#uris: ["/api/catalog", "/api/catalog/*", "/api/v2/catalog", "/api/v2/catalog/*"]#' gateways/apisix/apisix.yaml.bak > /tmp/apisix-v2.yaml
    cat /tmp/apisix-v2.yaml > gateways/apisix/apisix.yaml
    echo "Restauration : cat gateways/apisix/apisix.yaml.bak > gateways/apisix/apisix.yaml" ;;
  traefik)
    # Dossier monté (ro côté conteneur) : une modif sur l'hôte est vue par le watcher Traefik
    cp gateways/traefik/dynamic.yml /tmp/traefik-dynamic.bak
    sed -i.bak 's#rule: "PathPrefix(`/api/catalog`)"#rule: "PathPrefix(`/api/catalog`) || PathPrefix(`/api/v2/catalog`)"#' gateways/traefik/dynamic.yml
    echo "Restauration : cp /tmp/traefik-dynamic.bak gateways/traefik/dynamic.yml" ;;
  scg)
    echo "SCG : routes en application.yml -> rebuild + redémarrage (docker compose up -d --build scg)."
    echo "Alternative à chaud : POST /actuator/gateway/routes/{id} puis /actuator/gateway/refresh (non persistant)." ;;
esac
# NB : sur la v2 le backend répondra 404 (il ne sert que /api/catalog) ; on mesure la prise en compte de la ROUTE (≠ 404 gateway)
echo "Attente de la prise en compte de /api/v2/catalog..."
for i in $(seq 1 120); do
  hdrs=$(curl -s -D - -o /dev/null "$BASE/api/v2/catalog/1" -H 'X-Client-Id: reload' || true)
  if echo "$hdrs" | grep -qi '^x-instance:'; then   # réponse venue d'un BACKEND (en-tête X-Instance) = route active
    echo "Route active après $(( $(now_ms) - start )) ms"; exit 0; fi
  sleep 0.25
done
echo "Route non prise en compte après 30 s"
