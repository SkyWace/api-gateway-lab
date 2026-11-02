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
