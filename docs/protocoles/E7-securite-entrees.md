# E7 — Sécurité des entrées : CORS, en-têtes, requêtes malformées

**Objectif** — Vérifier la protection effective face à des requêtes hostiles ou mal formées, et ce que la gateway divulgue.

**Hypothèse**
- CORS : origine autorisée → en-têtes `Access-Control-Allow-*` ; origine inconnue → pas d'`Access-Control-Allow-Origin`.
- Path traversal `/api/catalog/../orders/1` normalisé en `/api/orders/1` → `401` (pas de contournement de l'auth).
- En-tête de 16 Ko : rejet `4xx` par NGINX (Kong, APISIX) ; Traefik (Go, limite 1 Mo par défaut) le laisse passer jusqu'au backend.
- Divulgation : Kong ajoute `Server: kong/x.y` et `Via` ; APISIX `Server: APISIX/x.y` → à masquer en production.

**Procédure**
1. `./scripts/smoke.sh <gw>` (sections CORS, requêtes malformées, en-têtes de réponse).
2. Compléter si temps : méthode `TRACE`, URL de 10 000 caractères, `Content-Length` incohérent (`curl --data-binary` + en-tête forcé).
3. TLS : hors périmètre mesuré ; décrire comment chaque solution le configure (cert statique, ACME natif chez Traefik, etc.).

**Résultat** (colonnes Traefik et SCG : non mesurées)

| Cas | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|
| CORS origine autorisée | OK (Allow-Origin/Methods/Headers, Max-Age 600) | OK | | |
| CORS origine refusée | renvoie l'origine configurée, pas l'origine hostile → bloqué par le navigateur | aucun `Access-Control-Allow-Origin` (plus strict que Kong) | | |
| Path traversal | normalisé → 401 (pas de contournement) | normalisé → 401 | | |
| En-tête 16 Ko | 400 (rejet NGINX) | 400 (rejet NGINX) | | |
| JSON invalide (relayé au backend → 400) | 400 | 400 | | |
| En-têtes divulgués | `Server`/`Via: kong/3.9.1`, `X-Kong-*` (latences, request-id) → `KONG_HEADERS=off` en prod | `Server: APISIX/3.11.0` ; détail des erreurs JWT dans `WWW-Authenticate` | | |
| TLS / ACME | | | | |

**Décision** — Les deux rejettent proprement les requêtes malformées et le path traversal. Les deux divulguent leur version (`Server`) : à masquer. APISIX est plus strict sur CORS mais trop bavard sur les erreurs JWT.
