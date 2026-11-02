# E3 — Rate limiting par client

**Objectif** — Mesurer la précision et l'équité du quota « 10 req/s par `X-Client-Id` » sur `/api/catalog`.

**Hypothèse**
- `client-greedy` (30 req/s) : ≈ 10 acceptées/s, ≈ 20 refusées/s en `429`, sur les 4.
- `client-polite` (5 req/s) : 0 refus (isolation entre clients).
- `client-burst` (rafales de 25) : **divergence attendue** selon l'algorithme — fenêtre fixe (Kong `rate-limiting`, APISIX `limit-count`) : ~10 acceptées par rafale, avec possibles « doubles fenêtres » à la frontière de la seconde ; token bucket (Traefik, SCG) : jusqu'au `burst` (10) puis lissage.
- Kong/APISIX/Traefik comptent **en mémoire locale** ; SCG dans Redis → seul SCG garde un quota exact si on scale la gateway à 2 instances.

**Environnement** — Une gateway à la fois. Pour SCG, Redis est démarré par le profil.

**Procédure**
1. `docker compose --profile tools run --rm k6 run /scripts/ratelimit.js -e TARGET=<gw>` (30 s).
2. Relever dans le résumé : `accepted{client:…}` et `limited_429{client:…}` par client.
3. Relever les en-têtes de quota renvoyés : `curl -si -H 'X-Client-Id: x' http://localhost:<port>/api/catalog/1 | grep -i ratelimit`.
4. Calculer : débit accepté/s du client gourmand = accepted / 30 ; écart au quota = (débit − 10) / 10.

**Mesures** — 3 répétitions ; accepté/s, % de 429, comportement en rafale, en-têtes informatifs.

**Résultat** — *à compléter*

| | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|
| Algorithme | fenêtre fixe | fenêtre fixe | token bucket | token bucket |
| greedy : accepté/s (écart au quota) | | | | |
| polite : nb de 429 | | | | |
| burst : acceptées par rafale | | | | |
| En-têtes `RateLimit-*` / `X-RateLimit-*` | | | | |
| Compteur partagé entre instances | non (local) | non (local) | non (local) | oui (Redis) |

**Décision** — *à compléter* (précision vs dépendance à Redis ; impact en HA).
