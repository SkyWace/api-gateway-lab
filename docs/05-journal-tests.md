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
