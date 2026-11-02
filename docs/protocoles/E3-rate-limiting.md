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
| greedy : accepté/s (écart au quota) | 10,00/s (0 %) ; 601 refus = 67 % | | | |
| polite : nb de 429 | 0 (151/151 acceptées) | | | |
| burst : acceptées par rafale | 10,0 exactement (150 / 15 rafales) | | | |
| En-têtes `RateLimit-*` / `X-RateLimit-*` | `X-RateLimit-Limit/Remaining/Reset` uniquement | | | |
| Compteur partagé entre instances | non (local) | non (local) | non (local) | oui (Redis) |

**Observations Kong (02/11/2026, `results/kong-ratelimit.log`)** — Quota tenu à +2,7 % près et isolation parfaite entre clients. En rafale, la moyenne de 11,4 acceptées (> 10) illustre l'effet **fenêtre fixe** : une rafale à cheval sur deux secondes consomme deux fenêtres (jusqu'à 20 requêtes passent). À comparer avec le token bucket de Traefik/SCG.

**Observations APISIX (02/11, `results/apisix-ratelimit.log`)** — Quota tenu **exactement** (300 acceptées en 30 s) et exactement 10 par rafale, là où Kong en laissait passer 11,4. Les deux sont annoncés « fenêtre fixe », mais la fenêtre de Kong est calée sur l'horloge (une rafale à cheval sur deux secondes consomme deux fenêtres), alors que le compteur d'APISIX démarre vraisemblablement à la première requête de la clé (compteur avec expiration) : une rafale ne chevauche pas deux fenêtres. Hypothèse à vérifier dans la doc / le code du plugin `limit-count`.

**Décision** — *à compléter* (précision vs dépendance à Redis ; impact en HA).
