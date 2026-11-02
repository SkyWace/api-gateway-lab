# Ports exposés sur l'hôte pour chaque gateway (tests manuels / smoke)
declare -A GW_PORT=( [kong]=8001 [apisix]=8002 [traefik]=8003 [scg]=8004 )
KEYCLOAK=${KEYCLOAK:-http://localhost:8080}
gw_url() { echo "http://localhost:${GW_PORT[$1]:?gateway inconnue: $1 (kong|apisix|traefik|scg)}"; }
get_token() {
  curl -s -X POST "$KEYCLOAK/realms/lab/protocol/openid-connect/token" \
    -d grant_type=client_credentials -d client_id=lab-client -d client_secret=lab-secret \
    | sed -E 's/.*"access_token":"([^"]+)".*/\1/'
}
