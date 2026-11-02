# E1 — Routage et maintenance des routes

**Objectif** — Vérifier que chaque gateway achemine `/api/catalog` (2 instances) et `/api/orders` (1 instance) correctement, renvoie un 404 propre pour une route inconnue et n'expose pas `/admin/chaos`. Évaluer l'effort de configuration.

**Hypothèse** — Les 4 solutions routent correctement (fonction de base). Différences attendues sur la *forme* : Kong et APISIX déclaratifs en YAML, Traefik très concis, SCG en YAML Spring + code Java pour les besoins non standard.

**Environnement** — `docker compose --profile <gw> up -d --build`, une gateway à la fois.

**Procédure**
1. `./scripts/smoke.sh <gw>` (section « Routage »).
2. Compter les lignes utiles de configuration nécessaires au parcours complet :
   `grep -cvE '^\s*(#|$)' <fichier(s) de config>`.
3. Noter le nombre de fichiers et de concepts à connaître (service, route, upstream, middleware…).

**Mesures** — 5 cas de routage OK/KO ; nb de lignes de config ; nb de concepts.

**Résultat** — *à compléter*

| | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|
| Cas OK / 5 | | | | |
| Lignes de config utiles | | | | |
| Concepts à maîtriser | | | | |
| Remarques | | | | |

**Décision** — *à compléter* (ex. : simplicité de lecture vs richesse d'expression).
