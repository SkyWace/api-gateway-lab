#!/usr/bin/env bash
# Affiche un access token Keycloak (client_credentials) — usage : TOKEN=$(./scripts/token.sh)
set -euo pipefail
source "$(dirname "$0")/env.sh"
get_token
