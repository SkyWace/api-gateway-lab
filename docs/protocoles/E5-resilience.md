# E5 — Service indisponible, répartition et résilience (expérience disponibilité)

**Objectif** — Observer ce que voit le client quand un backend tombe, ralentit ou renvoie des erreurs, et vérifier l'équilibrage sur 2 instances.

**Hypothèse**
- **Répartition** : ≈ 50/50 sur `catalog-1` / `catalog-2` (round-robin) pour les 4.
- **Perte de catalog-2** : quelques erreurs (≤ 1 %) le temps que les health checks / retries l'écartent, puis 100 % de succès sur catalog-1 ; réintégration automatique au redémarrage.
- **orders lent (7 s)** : réponse `504` (Kong, APISIX, Traefik) ou `503` via fallback (SCG) en ≈ 5 s, pas d'attente de 7 s.
- **orders en erreur 50 %** : circuit ouvert après quelques échecs chez APISIX (`api-breaker`), Traefik (`circuitBreaker`) et SCG (Resilience4j) → réponses rapides `503` ; Kong OSS n'a pas de circuit breaker → le client continue de recevoir les 500 du backend.

**Procédure**
1. Répartition : `... loadbalancing.js -e TARGET=<gw>` → compteurs `hits{instance:…}`.
2. Pour chaque scénario `kill-catalog2`, `slow-orders`, `errors-orders`, `kill-orders` :
   - terminal 1 : `docker compose --profile tools run --rm k6 run /scripts/resilience.js -e TARGET=<gw> -e ENDPOINT=<catalog|orders> 2>&1 | tee results/<gw>-<scenario>.log`
   - terminal 2, après ~20 s : `./scripts/chaos.sh <scenario>`
   - export : `./scripts/csv-from-log.sh results/<gw>-<scenario>.log > results/<gw>-<scenario>.csv`
3. Tracer statut et durée dans le temps (tableur ou script) en superposant les horodatages de `results/chaos-events.log`.
4. `./scripts/chaos.sh reset` entre deux runs.

**Mesures** — répartition par instance ; nb et % d'erreurs ; durée de la fenêtre d'erreurs ; temps de réponse max ; code renvoyé au client ; temps de réintégration.

**Résultat** — *à compléter*

| | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|
| Répartition catalog-1 / catalog-2 | 500 / 500 (round-robin exact) | 500 / 500 (round-robin exact) | | |
| kill-catalog2 : erreurs (nb, %) | 0 / 2 400 (0 %) | 0 / 2 401 (0 %) | | |
| kill-catalog2 : réintégration (s) | ≈ 5 (hors rotation ≈ 35 s pour 31 s d'arrêt) | ≈ 5 (c2 hors rotation ≈ 36 s pour ≈ 31 s d'arrêt) | | |
| slow-orders : code / durée max | | | | |
| errors-orders : circuit ouvert ? code client | « oui » de fait : 503 après 3 échecs… **et ne se referme jamais** (2 × 200, 3 × 500, puis 2 396 × 503) | oui : 503 rapides pendant la panne, **refermé ≈ 10 s après la fin** ; 24 × 500 + 563 × 503 sur 2 400 (24 %) | | |
| kill-orders : code client | | | | |

**Observations Kong — kill-catalog2 (02/11, `results/kong-kill-catalog2.log`, `results/chaos-events.log`)**
Arrêt de catalog-2 de 13:41:51 à 13:42:22 (31 s) sous 20 req/s pendant 120 s. Résultat : 2 400 réponses **toutes en 200**, P95 7,7 ms, max 159 ms. Répartition : catalog-1 = 1 555, catalog-2 = 845. En régime normal catalog-2 aurait reçu ≈ 1 200 requêtes ; il en manque 355, soit ≈ 35,5 s hors rotation → ≈ 31 s d'arrêt + ≈ 5 s pour être réintégré (intervalle du health check actif). Les requêtes tombées sur catalog-2 au moment de l'arrêt ont été **rejouées sur catalog-1** (retries = 2) : aucun impact visible côté client.

**Observations Kong — errors-orders (02/11, `results/kong-errors-orders.log`)**
Injection de 50 % d'erreurs 500 sur orders (seule instance) à 13:46:27, pendant 30 s, sous 20 req/s.
Résultat : 2 réponses 200, **3 réponses 500**, puis **2 396 réponses 503** générées par Kong (aucune n'atteint le backend : `instance:none`).
Explication : le **health check passif** de l'upstream `orders` (`http_failures: 3`) a marqué l'unique cible « unhealthy » après 3 erreurs → Kong répond 503 (*failure to get a peer from the ring-balancer*). Cela joue le rôle d'un circuit breaker… mais **sans demi-ouverture** : sans health check *actif* sur cet upstream, un passif ne remet jamais une cible en service. La panne réelle a duré 30 s, l'indisponibilité vue par le client a duré **tout le reste du test** (et jusqu'au redémarrage de Kong).
Conséquence pour la décision : avec Kong OSS, tout upstream doit avoir un health check **actif** en plus du passif, sinon une rafale d'erreurs courte provoque une coupure durable. À comparer au circuit breaker d'APISIX (`api-breaker`, réouverture progressive) et de Traefik/SCG.

**Observations APISIX — errors-orders (02/11, `results/apisix-errors-orders.log`)**
50 % d'erreurs 500 injectées de 14:19:25 à 14:19:55. Chronologie par tranches de 10 s (`scripts/timeline.sh`) :

| Tranche (s) | 200 | 500 (backend) | 503 (circuit ouvert) |
|---|---|---|---|
| 0–10 (début de panne) | 75 | 6 | 119 |
| 10–20 | 4 | 5 | 191 |
| 20–30 | 8 | 9 | 183 |
| 30–40 (fin de panne) | 126 | 4 | 70 |
| 40–120 | 1 599 | 0 | 0 |

Le plugin `api-breaker` ouvre le circuit après 3 échecs, laisse passer quelques requêtes de test (les 200/500 isolés pendant la panne = demi-ouverture), puis **se referme moins de 10 s après le retour du backend**. Erreurs vues par le client : 24 % du run, toutes concentrées dans la fenêtre de panne. Comparaison Kong (même scénario) : 99,9 % d'erreurs, **aucune récupération**.

**Décision** — *à compléter*. Question du sujet : *comment une erreur backend se répercute-t-elle sur le client ?*
