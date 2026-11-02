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
| P50 catalog (ms) | | | | | |
| P95 catalog (ms) | | | | | |
| P99 catalog (ms) | | | | | |
| Surcoût P95 catalog (ms) | — | | | | |
| P95 orders avec JWT (ms) | | | | | |
| RPS max soutenu | | | | | |
| CPU au palier max (%) | | | | | |
| RAM max (Mo) | | | | | |

**Limites de validité** — Docker sur un poste de dev ≠ production ; k6 partage le CPU de l'hôte ; pas de TLS ; résultats à relire en *relatif* entre solutions, pas en absolu.

**Décision** — *à compléter*.
