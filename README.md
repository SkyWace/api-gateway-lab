# Lab — Comparatif de solutions API Gateway

POC reproductible comparant **Kong Gateway OSS**, **Apache APISIX**, **Traefik Proxy** et **Spring Cloud Gateway** sur un même parcours, dans un contexte **microservices** (point d'entrée unique, résilience, observabilité).

| Document | Contenu |
|---|---|
| [docs/01-cadrage.md](docs/01-cadrage.md) | Contexte, acteurs, flux, contraintes, volumes, critères de succès et éliminatoires |
| [docs/02-architecture.md](docs/02-architecture.md) | Schéma, versions, ressources, ports, natif vs plugin vs payant |
| [docs/protocoles/](docs/protocoles/) | 8 fiches d'expérience (E1 → E8) |
| [docs/03-matrice-decision.md](docs/03-matrice-decision.md) | Pondération, barème, matrice à remplir |
| [docs/04-note-decision.md](docs/04-note-decision.md) | Note de décision (brouillon à compléter avec les mesures) |
| [docs/05-journal-tests.md](docs/05-journal-tests.md) | Journal des exécutions |
| [docs/graphs/](docs/graphs/README.md) | Graphiques générés depuis `results/` (`python3 scripts/graphs.py`) |

## Prérequis

- Docker ≥ 24 avec Docker Compose v2 (≥ 4 vCPU et 8 Go de RAM alloués à Docker recommandés)
- `curl`, `bash` (Linux, macOS, ou WSL2 sous Windows)
- Accès internet au premier lancement (images Docker, dépendances Maven pour SCG, bibliothèque k6-summary)

## Démarrage rapide

```bash
# 1. Lancer le socle + UNE gateway (kong | apisix | traefik | scg)
docker compose --profile kong up -d --build
docker compose ps                       # attendre que keycloak soit "healthy" (~30 s)

# 2. Vérifier le parcours
./scripts/smoke.sh kong

# 3. Lancer une expérience
docker compose --profile tools run --rm k6 run /scripts/latency.js -e TARGET=kong

# 4. Changer de gateway
docker compose --profile kong down
docker compose --profile apisix up -d
```

Premier build de SCG : 3 à 5 min (téléchargement Maven). Les suivants sont mis en cache.

## Parcours commun

| Route | Backend | Politiques |
|---|---|---|
| `GET /api/catalog[/{id}]` | `catalog-1` + `catalog-2` (round-robin) | public, 10 req/s par `X-Client-Id`, CORS `http://localhost:5173` |
| `GET/POST /api/orders[/{id}]` | `orders` | JWT Keycloak obligatoire, timeout 5 s, retries, circuit breaker si disponible |

Token de test : `TOKEN=$(./scripts/token.sh)` puis `curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/orders/1`

## Expériences

| # | Expérience | Commande principale |
|---|---|---|
| E1 | Routage | `./scripts/smoke.sh <gw>` |
| E2 | Authentification (sécurité) | `k6 run /scripts/auth.js -e TARGET=<gw>` |
| E3 | Rate limiting | `k6 run /scripts/ratelimit.js -e TARGET=<gw>` |
| E4 | Latence / débit (performance) | `latency.js`, `throughput.js` + `./scripts/stats.sh <gw>` |
| E5 | Résilience / répartition (disponibilité) | `resilience.js`, `loadbalancing.js` + `./scripts/chaos.sh <scénario>` |
| E6 | Observabilité | `docker compose --profile obs up -d prometheus` |
| E7 | Sécurité des entrées | `./scripts/smoke.sh <gw>` |
| E8 | Déploiement à chaud | `./scripts/reload.sh <gw>` |

(`k6 run …` = `docker compose --profile tools run --rm k6 run …`)

Tous les résultats sont écrits dans `results/` (JSON k6, logs, CSV CPU/RAM). Le score de la matrice se calcule avec `python3 scripts/score.py`.

## Arborescence

```
├── docker-compose.yml          # socle + 1 profil par gateway + outils
├── backends/                   # API factice (Node, zéro dépendance) + jeux de données
├── auth-validator/             # validation JWT externalisée (Traefik forwardAuth)
├── identity/                   # realm Keycloak + clé RSA de TEST
├── gateways/
│   ├── kong/kong.yml           # DB-less déclaratif
│   ├── apisix/                 # standalone (config.yaml + apisix.yaml)
│   ├── traefik/                # traefik.yml (statique) + dynamic.yml
│   └── scg/                    # projet Maven Spring Boot
├── tests/k6/                   # scripts de charge et fonctionnels
├── scripts/                    # smoke, chaos, stats, reload, token, score
├── observability/              # prometheus.yml
├── results/                    # sorties des tests
└── docs/                       # cadrage, architecture, protocoles, matrice, note
```

## Sécurité du dépôt

`identity/keys/` contient une paire de clés RSA **générée uniquement pour ce lab**, ainsi que des secrets de test (`lab-secret`, `admin/admin`). Ne jamais réutiliser hors du POC.

## Dépannage

| Symptôme | Piste |
|---|---|
| `401` partout sur `/api/orders` | Keycloak pas encore prêt, ou token demandé avant l'import du realm : `docker compose logs keycloak` |
| APISIX ne démarre pas | `docker compose logs apisix` ; le fichier `apisix.yaml` doit finir par `#END` |
| SCG en erreur au démarrage | Redis / Keycloak pas prêts : `docker compose --profile scg restart scg` |
| Kong : `no Route matched` | Vérifier `docker compose logs kong` (erreur de parsing de `kong.yml`) |
| k6 : `dropped_iterations` | Le générateur sature : baisser `RATE`, ou augmenter `preAllocatedVUs` |
| Limites CPU/RAM à vérifier | `./scripts/check-limits.sh` : aucune ligne ne doit afficher AUCUNE |
| Ports déjà utilisés | Adapter la section `ports` du compose et `scripts/env.sh` |
