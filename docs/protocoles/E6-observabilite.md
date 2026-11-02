# E6 — Observabilité

**Objectif** — Vérifier qu'on peut suivre une requête de bout en bout (identifiant de corrélation) et exploiter des métriques.

**Hypothèse**
- Kong (`correlation-id`), APISIX (`request-id`) et SCG (filtre global) génèrent un `X-Request-ID`, le propagent au backend et le renvoient au client.
- Traefik OSS ne génère pas d'identifiant : il ne fait que transmettre un `X-Request-ID` fourni par le client (corrélation possible via le tracing OpenTelemetry, non activé ici).
- Les 4 exposent des métriques Prometheus ; Kong et APISIX fournissent nativement latence gateway vs latence upstream.

**Procédure**
1. `curl -si http://localhost:<port>/api/catalog/1` : l'en-tête `X-Request-ID` est-il renvoyé ? Le corps (`headersSeen`) montre-t-il le même ID côté backend ?
2. `curl -si -H 'X-Request-ID: test-123' ...` : l'ID fourni est-il conservé ?
3. Retrouver l'ID dans les logs : `docker compose logs <gw> | grep <id>`.
4. `docker compose --profile obs up -d prometheus` → http://localhost:9090, requêtes :
   - Kong : `kong_http_requests_total`, `kong_request_latency_ms_bucket`
   - APISIX : `apisix_http_status`, `apisix_http_latency_bucket`
   - Traefik : `traefik_service_requests_total`, `traefik_service_request_duration_seconds_bucket`
   - SCG : `spring_cloud_gateway_requests_seconds_count`, `http_server_requests_seconds_bucket`
5. Après E3/E5, vérifier qu'on voit les 429 et les 5xx dans les métriques.

**Résultat** — *à compléter*

| | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|
| ID généré si absent | | | | |
| ID client conservé | | | | |
| ID visible côté backend | | | | |
| ID dans les logs gateway | | | | |
| Latence gateway vs upstream séparée | | | | |
| 429 / 5xx visibles en métriques | | | | |
| Effort de mise en place | | | | |

**Décision** — *à compléter*.
