# Journal de tests

## Machine hôte

| Élément | Valeur |
|---|---|
| CPU (modèle, cœurs) | |
| RAM | |
| OS | |
| Docker / Compose | `docker version`, `docker compose version` |
| Date des mesures | |

## Journal

Une ligne par exécution, y compris les runs ratés (ils font partie de la démarche).

| Date/heure | Exp. | Gateway | Commande / paramètres | Fichier résultat | Résultat clé | Incident / remarque |
|---|---|---|---|---|---|---|
| 02/11 09:28 | E1/E7 | kong | `smoke.sh kong` | `results/kong-smoke-20261102-092821.log` | — | Keycloak non démarré (port 8080 occupé) → déplacé sur 8180 ; bug bash 3.2 corrigé |
| 02/11 09:30 | E1/E7 | kong | `smoke.sh kong` | `results/kong-smoke-20261102-093047.log` | 13 OK / 0 KO | Critère CORS du script corrigé ensuite (origine renvoyée ≠ origine hostile) |
| 02/11 09:33 | E2 | kong | `auth.js` | `results/kong-auth.log` | 9/9 conformes | |
| 02/11 09:34 | E3 | kong | `ratelimit.js` (30 s) | `results/kong-ratelimit.log` | greedy 10,27/s, polite 0 refus, burst 11,4/rafale | |
| 02/11 09:35 | E4 | direct | `latency.js` 200 req/s 60 s | `results/direct-latency-1.log` | P50 0,77 / P95 2,10 / P99 4,61 ms, 0 % erreur | Run 1/3 |
| | | | | | | |
| 02/11 ~09:40 | E4 | direct | `latency.js` | `results/direct-latency-2.log` | P50 0,80 / P95 2,16 / P99 5,22 ms | Run 2/3 ; run 3 à refaire (commentaire `#` collé dans zsh) |
| 02/11 ~09:42 | E4 | kong | `latency.js DURATION=30s` | — | P95 3,39 ms | Échauffement, jeté |
| 02/11 ~09:43 | E4 | kong | `latency.js` | `results/kong-latency-1.log` | P50 1,55 / P95 3,55 / P99 5,65 ms | Propre |
| 02/11 ~09:45 | E4 | kong | `latency.js` | `results/kong-latency-2.log` | P50 1,63 / P95 15,48 / P99 120 ms | 118 dropped_iterations → hôte saturé, à rejouer |
| 02/11 ~09:47 | E4 | kong | `latency.js` | `results/kong-latency-3.log` | P50 1,74 / P95 7,37 / P99 79,9 ms | 15 dropped_iterations → à rejouer |
| 02/11 09:49 | E4 | kong | `latency.js ENDPOINT=orders` | — | échec setup() | Token Keycloak non obtenu (réponse vide) → vérifier l'état de Keycloak |
| 02/11 ~09:52 | E4 | direct | `latency.js` | `results/direct-latency-3.log` | P50 0,75 / P95 2,10 / P99 4,16 ms | Run 3/3 |
| 02/11 ~09:54 | E4 | kong | `latency.js` (rejeu) | `results/kong-latency-2.log` | P50 1,57 / P95 4,06 / P99 19,6 ms | 0 dropped |
| 02/11 ~09:56 | E4 | kong | `latency.js` (rejeu) | `results/kong-latency-3.log` | P50 1,83 / P95 3,65 / P99 5,61 ms | 0 dropped |
| 02/11 09:57 | E4 | kong | `latency.js ENDPOINT=orders` | — | échec setup() | Cause : bug du script (discardResponseBodies vidait la réponse token) → corrigé |
| 02/11 ~10:03 | E4 | kong | `throughput.js` (300→3000 req/s) | `results/kong-throughput.log` | 253 315 req, 0 % erreur, moy. 1 447 req/s ; 12 425 dropped ; P95 global 91,8 ms, P99 518 ms | Résumé non ventilé par palier → script amélioré, run à refaire |
| 02/11 ~10:09 | E4 | kong | `throughput.js` (par palier) | `results/kong-throughput.log` | 0 % erreur ; palier 3 000 servi à 100 %, P95 18,7 ms ; pertes aux paliers 1 500/2 250 | Pertes = allocation de VU par k6 → preAllocatedVUs 200 → 600 |
| 02/11 ~10:14 | E4 | kong | `throughput.js` (600 VU pré-alloués) + `stats.sh` | `results/kong-throughput.log`, `results/kong-stats-20261102-101355.csv` | ≈ 100 % servi à tous les paliers, 0 erreur, P95 25,7 ms à 3 000 req/s ; pic 120 % CPU / 206 Mo | Run retenu. Queues élevées aux paliers bas = bruit hôte. CPU > 100 % → vérifier NanoCpus |
| 02/11 ~10:20 | E4 | kong | `latency.js ENDPOINT=orders` | `results/kong-latency-orders.log` | P50 1,61 / P95 14,55 / P99 173 ms, 0 % erreur | 53 dropped ; sans limite CPU |
| 02/11 ~10:25 | E5 | kong | `loadbalancing.js` (1 000 req) | `results/kong-lb.log` | catalog-1 : 500 / catalog-2 : 500 | Round-robin exact |
| 02/11 11:08 | — | kong | `docker inspect` | — | NanoCpus = 0, Memory = 512 Mo | **Limite CPU non appliquée** depuis le début → compose corrigé (`deploy.resources`), perf Kong à rejouer |
| 02/11 ~11:35 | E4 | kong | `latency.js` ×3 + orders, **limite 1 vCPU vérifiée** | `results/kong-latency-{1,2,3,orders}.log` | P50 1,62 / P95 3,70 / P99 6,95 ms ; orders P95 3,58 ms ; 0 dropped | Remplace les mesures sans limite CPU |
| 02/11 ~13:30 | E4 | kong | `throughput.js` + `stats.sh`, **limite 1 vCPU vérifiée** | `results/kong-throughput.log` | 100 % servi à tous les paliers, 0 erreur ; P95 36 ms à 3 000 req/s ; CPU 97 %, RAM ~205 Mo | Run retenu. Saturation proche (CPU plafonné, P99 > 100 ms dès 1 500) |
| 02/11 13:41 | E5 | kong | `resilience.js ENDPOINT=catalog` + `chaos.sh kill-catalog2` | `results/kong-kill-catalog2.log` | 2 400 × 200, 0 erreur ; c1 1 555 / c2 845 | Failover transparent, réintégration ≈ 5 s |
| 02/11 13:46 | E5 | kong | `resilience.js ENDPOINT=orders` + `chaos.sh errors-orders` | `results/kong-errors-orders.log` | 2 × 200, 3 × 500, 2 396 × 503 | Upstream marqué unhealthy par le health check passif, jamais réintégré (pas de check actif) → indisponibilité durable |
| 02/11 13:54 | E1/E7 | apisix | `smoke.sh apisix` | `results/apisix-smoke-20261102-135445.log` | 1 OK / 13 KO (code 000 = aucune réponse) | APISIX ne démarrait pas : `APISIX_STAND_ALONE` fait réécrire `config.yaml` par l'entrypoint alors qu'il est monté en lecture seule → variable retirée, conteneur recréé |
| 02/11 13:59 | E1/E7 | apisix | `smoke.sh apisix` | `results/apisix-smoke-20261102-135923.log` | 14 OK / 0 KO | Après correctif de démarrage |
| 02/11 ~14:00 | E2 | apisix | `auth.js` | `results/apisix-auth.log` | 9/9 conformes | Messages d'erreur JWT très détaillés |
| 02/11 ~14:01 | E3 | apisix | `ratelimit.js` | `results/apisix-ratelimit.log` | greedy 10,00/s, polite 0 refus, burst 10/rafale | Quota exact |
| 02/11 ~14:02 | E5 | apisix | `loadbalancing.js` | `results/apisix-lb.log` | 500 / 500 | |
| 02/11 ~14:12 | E4 | apisix | `throughput.js` + `stats.sh` | `results/apisix-throughput.log` | ≈ 100 % servi, 0 erreur ; P95 1,6 ms à 3 000 req/s ; CPU 53 %, RAM 52 Mo | |
| 02/11 14:19 | E5 | apisix | `resilience.js ENDPOINT=orders` + `chaos.sh errors-orders` | `results/apisix-errors-orders.log` | 1 813 × 200, 24 × 500, 563 × 503 | Circuit ouvert pendant la panne, refermé < 10 s après |
| 02/11 ~14:24 | E5 | apisix | `resilience.js ENDPOINT=catalog` + `chaos.sh kill-catalog2` | `results/apisix-kill-catalog2.log` | 2 401 × 200, 0 erreur ; c1 1 565 / c2 836 | Failover transparent, identique à Kong |
| 02/11 ~14:08 | E4 | apisix | `latency.js` ×3 + orders | `results/apisix-latency-{1,2,3,orders}.log` | P50 1,51 / P95 2,68 / P99 5,38 ms ; orders P50 2,04 / P95 3,67 ms ; 0 dropped | |
