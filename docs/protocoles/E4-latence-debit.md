# E4 — Latence et débit (expérience performance)

**Objectif** — Mesurer le surcoût de latence de chaque gateway par rapport à un appel direct, puis son débit max sous 1 vCPU / 512 Mo.

**Hypothèse**
- À 200 req/s, surcoût P95 de quelques ms pour Kong, APISIX et Traefik ; SCG légèrement au-dessus (pile réactive JVM) mais sous le seuil S3 (+10 ms) après échauffement.
- En débit, Kong et APISIX (NGINX/OpenResty) saturent le plus tard ; Traefik ensuite ; SCG plafonne plus tôt et consomme le plus de RAM.
- Sur `/api/orders`, Traefik paie un saut réseau supplémentaire (forwardAuth) → surcoût plus élevé que sur `/api/catalog`.

**Environnement** — Une seule gateway lancée ; machine hôte au repos (fermer IDE/navigateur si possible) ; noter CPU/RAM de l'hôte.

**Procédure**
1. Baseline : `docker compose --profile tools run --rm k6 run /scripts/latency.js -e TARGET=direct`
2. Pour chaque gateway :
   - échauffement : `... latency.js -e TARGET=<gw> -e DURATION=30s` (résultat jeté) ;
   - 3 mesures : `... latency.js -e TARGET=<gw>` (200 req/s, 60 s) ;
   - route protégée : `... latency.js -e TARGET=<gw> -e ENDPOINT=orders`.
3. Débit : terminal 1 `./scripts/stats.sh <gw>` ; terminal 2 `... throughput.js -e TARGET=<gw>` (paliers 300 → 3 000 req/s).
4. Point de saturation = premier palier où `http_req_failed` > 1 % **ou** P95 > 100 ms **ou** k6 signale `dropped_iterations`.

**Mesures** — P50 / P95 / P99 (`med`, `p(95)`, `p(99)` du résumé `http_req_duration`) ; surcoût = gateway − direct ; RPS max soutenu ; CPU % et RAM max (`results/<gw>-stats-*.csv`).

**Résultat** — *à compléter* (médiane de 3 runs)

| | Direct | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|---|
| P50 catalog (ms) | 0,77 | | | | |
| P95 catalog (ms) | 2,10 | | | | |
| P99 catalog (ms) | 4,61 | | | | |
| Surcoût P95 catalog (ms) | — | | | | |
| P95 orders avec JWT (ms) | | | | | |
| RPS max soutenu | | | | | |
| CPU au palier max (%) | | | | | |
| RAM max (Mo) | | | | | |

**Mesures brutes (200 req/s, 60 s, route catalog)**

| Run | Cible | P50 (ms) | P95 (ms) | P99 (ms) | Erreurs | dropped_iterations | Fichier |
|---|---|---|---|---|---|---|---|
| 1 | direct | 0,77 | 2,10 | 4,61 | 0 % | 0 | `direct-latency-1.log` |
| 2 | direct | 0,80 | 2,16 | 5,22 | 0 % | 0 | `direct-latency-2.log` |
| 3 | direct | | | | | | `direct-latency-3.log` |
| échauffement | kong (30 s) | 1,30 | 3,39 | 6,81 | 0 % | 0 | jeté |
| 1 | kong | 1,55 | 3,55 | 5,65 | 0 % | 0 | `kong-latency-1.log` |
| 2 | kong | 1,63 | 15,48 | 120,02 | 0 % | **118** | `kong-latency-2.log` |
| 3 | kong | 1,74 | 7,37 | 79,86 | 0 % | **15** | `kong-latency-3.log` |

> Règle de validité adoptée : un run avec `dropped_iterations` > 0 signale que **le générateur (k6) ou l'hôte** a saturé, pas forcément la gateway. Ces runs sont rejoués machine au repos ; s'ils restent bruités, ils sont conservés et signalés. Machine : MacBook Air (refroidissement passif → bridage thermique possible sous charge prolongée, d'où une pause de 1–2 min entre runs).
>
> Lecture provisoire Kong : la **médiane** est stable (+0,8 à +1 ms vs direct) ; les écarts portent sur la **queue** (P95/P99), sensible au bruit de l'hôte.

**Limites de validité** — Docker sur un poste de dev ≠ production ; k6 partage le CPU de l'hôte ; pas de TLS ; résultats à relire en *relatif* entre solutions, pas en absolu.

**Décision** — *à compléter*.
