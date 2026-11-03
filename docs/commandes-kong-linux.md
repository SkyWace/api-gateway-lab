# Commandes de test Kong — E1 à E8 (Linux)

Toutes les commandes se lancent depuis la racine du dépôt, dans un terminal bash.

> **Version automatique** : `./scripts/run-all.sh kong` enchaîne tout ce qui suit (E1 → E8, ≈ 25 min, pannes et stats lancées en arrière-plan) et affiche un résumé. Le détail ci-dessous sert à rejouer une étape à la main.

## 0. Préparation (une fois)

```bash
# Docker + Compose v2 (Debian/Ubuntu), si absents
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git curl python3 python3-matplotlib
sudo usermod -aG docker "$USER" && newgrp docker      # docker sans sudo

git clone https://github.com/SkyWace/api-gateway-lab && cd api-gateway-lab
chmod +x scripts/*.sh

# Raccourci k6 (à recharger dans chaque nouveau terminal)
k6run() { docker compose --profile tools run --rm k6 run "$@"; }
```

## 1. Démarrer Kong

```bash
docker compose --profile kong up -d --build
docker compose --profile kong ps        # attendre keycloak "healthy" (~30-60 s)
./scripts/check-limits.sh               # attendu : kong 1,00 / 512 ; backends 0,50 / 256
```

## E1 + E7 — Routage et sécurité des entrées

```bash
./scripts/smoke.sh kong
```

## E2 — Authentification

```bash
k6run /scripts/auth.js -e TARGET=kong 2>&1 | tee results/kong-auth.log
```

## E3 — Rate limiting

```bash
k6run /scripts/ratelimit.js -e TARGET=kong 2>&1 | tee results/kong-ratelimit.log
```

## E4 — Latence et débit

```bash
# Baseline sans gateway (3 runs)
k6run /scripts/latency.js -e TARGET=direct 2>&1 | tee results/direct-latency-1.log
k6run /scripts/latency.js -e TARGET=direct 2>&1 | tee results/direct-latency-2.log
k6run /scripts/latency.js -e TARGET=direct 2>&1 | tee results/direct-latency-3.log

# Kong : échauffement (jeté) puis 3 runs + route protégée
k6run /scripts/latency.js -e TARGET=kong -e DURATION=30s
k6run /scripts/latency.js -e TARGET=kong 2>&1 | tee results/kong-latency-1.log
k6run /scripts/latency.js -e TARGET=kong 2>&1 | tee results/kong-latency-2.log
k6run /scripts/latency.js -e TARGET=kong 2>&1 | tee results/kong-latency-3.log
k6run /scripts/latency.js -e TARGET=kong -e ENDPOINT=orders 2>&1 | tee results/kong-latency-orders.log

grep -HE "http_req_duration|dropped_iterations" results/*-latency-*.log
```

Débit — **deux terminaux** :

```bash
# Terminal 1
./scripts/stats.sh kong

# Terminal 2 (~3 min)
k6run /scripts/throughput.js -e TARGET=kong 2>&1 | tee results/kong-throughput.log
# puis Ctrl+C dans le terminal 1

grep -E "palier|dropped" results/kong-throughput.log
sort -t';' -k2 -n "$(ls -t results/kong-stats-*.csv | head -1)" | tail -3
```

## E5 — Répartition et résilience

```bash
k6run /scripts/loadbalancing.js -e TARGET=kong 2>&1 | tee results/kong-lb.log
```

Chaque scénario : **deux terminaux**, panne lancée ~20 s après le début du test, puis `reset`.

```bash
# 1) Perte d'une instance catalogue
#   T1 :
k6run /scripts/resilience.js -e TARGET=kong -e ENDPOINT=catalog 2>&1 | tee results/kong-kill-catalog2.log
#   T2 :
./scripts/chaos.sh kill-catalog2

# 2) Backend en erreur (50 % de 500)
#   T1 :
k6run /scripts/resilience.js -e TARGET=kong -e ENDPOINT=orders 2>&1 | tee results/kong-errors-orders.log
#   T2 :
./scripts/chaos.sh errors-orders

# 3) Backend lent (7 s > timeout 5 s)
#   T1 :
k6run /scripts/resilience.js -e TARGET=kong -e ENDPOINT=orders 2>&1 | tee results/kong-slow-orders.log
#   T2 :
./scripts/chaos.sh slow-orders

# 4) Backend arrêté
#   T1 :
k6run /scripts/resilience.js -e TARGET=kong -e ENDPOINT=orders 2>&1 | tee results/kong-kill-orders.log
#   T2 :
./scripts/chaos.sh kill-orders

# Entre deux scénarios (remet les backends à zéro ET redémarre Kong)
./scripts/chaos.sh reset
```

Lecture :

```bash
grep -E "status:|instance:" results/kong-*-orders.log results/kong-kill-catalog2.log
./scripts/timeline.sh results/kong-errors-orders.log 10
cat results/chaos-events.log
```

## E6 — Observabilité

```bash
# Corrélation : ID généré, renvoyé, vu par le backend
curl -si http://localhost:8001/api/catalog/1 | grep -iE "x-request-id|x-kong"
curl -s -H 'X-Request-ID: test-123' http://localhost:8001/api/catalog/1 | grep -o '"headersSeen":{[^}]*}'
docker compose --profile kong logs kong | grep test-123

# Métriques brutes de Kong
curl -s http://localhost:18100/metrics | grep -E "^kong_(http_requests_total|request_latency_ms_count|upstream_target_health)" | head -20

# Prometheus (requêtes via l'API, pas besoin de navigateur)
docker compose --profile obs up -d prometheus
sleep 15
curl -s 'http://localhost:9090/api/v1/query?query=sum(kong_http_requests_total)%20by%20(code)'
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(kong_request_latency_ms_bucket[1m]))%20by%20(le))'
```

## E8 — Changement de route à chaud

```bash
# Terminal 1 (trafic continu pendant le changement)
k6run /scripts/latency.js -e TARGET=kong -e RATE=50 -e DURATION=90s 2>&1 | tee results/kong-reload.log

# Terminal 2, ~10 s après
./scripts/reload.sh kong 2>&1 | tee results/kong-reload-delay.log

# Restauration (Kong relit kong.yml)
docker compose --profile kong restart kong
```

## Fin

```bash
docker compose --profile kong logs kong > results/kong-gateway.log
python3 scripts/graphs.py
git add results docs/graphs && git commit -m "Résultats Kong (Linux)" && git push
docker compose --profile kong --profile obs down
```
