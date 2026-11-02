# Ports exposés sur l'hôte pour chaque gateway (tests manuels / smoke)
# Compatible bash 3.2 (macOS) : pas de tableau associatif.
KEYCLOAK=${KEYCLOAK:-http://localhost:8080}
gw_port() {
  case "$1" in
    kong) echo 8001 ;; apisix) echo 8002 ;; traefik) echo 8003 ;; scg) echo 8004 ;;
    *) echo "gateway inconnue: $1 (kong|apisix|traefik|scg)" >&2; return 1 ;;
  esac
}
gw_url() { local p; p=$(gw_port "$1") || exit 1; echo "http://localhost:$p"; }
# Horodatage en millisecondes, portable macOS/Linux
now_ms() { python3 -c 'import time; print(int(time.time()*1000))'; }
get_token() {
  curl -s -X POST "$KEYCLOAK/realms/lab/protocol/openid-connect/token" \
    -d grant_type=client_credentials -d client_id=lab-client -d client_secret=lab-secret \
    | sed -E 's/.*"access_token":"([^"]+)".*/\1/'
}
