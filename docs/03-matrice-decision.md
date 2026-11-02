# 3. Matrice de décision

## 3.1 Critères éliminatoires (vérifiés avant tout score)

| Critère | Kong OSS | APISIX | Traefik OSS | SCG | Preuve |
|---|---|---|---|---|---|
| E1 — JWT + rate limiting sans licence | ✅ (jwt statique) | ✅ (OIDC/JWKS) | non mesuré | non mesuré | E2, E3 |
| E2 — Config versionnable dans Git | ✅ (`kong.yml`) | ✅ (`apisix.yaml`) | non mesuré | non mesuré | dépôt |
| E3 — Métriques Prometheus | ✅ plugin actif* | ✅ plugin actif* | non mesuré | non mesuré | E6 (*capture Prometheus non réalisée) |
| E4 — Déployable sur Kubernetes | ✅ (doc) | ✅ (doc) | non mesuré | non mesuré | doc officielle (Ingress Controller / Helm), non testé |

> Point d'attention E1 pour Traefik : la validation JWT est faite par un service **externe** écrit pour le POC. Décider explicitement si cela « passe » (fonction obtenue sans licence) ou non (fonction absente du produit) — et l'écrire dans la note.

## 3.2 Pondération (contexte microservices)

| Critère | Poids | Pourquoi ce poids |
|---|---|---|
| Routage et politiques | 15 % | Indispensable mais couvert par toutes les solutions |
| Sécurité / contrôle d'accès | 20 % | Point d'entrée unique = surface d'attaque unique |
| Débit et latence | 15 % | Le pic visé (1 500 req/s) est modeste ; on vérifie surtout l'absence de goulot |
| Résilience | 20 % | Problématique n°1 du contexte microservices (pannes en cascade) |
| Observabilité | 15 % | Problématique n°2 du contexte (diagnostic multi-services) |
| Complexité d'exploitation | 10 % | Config, mises à jour, compétences de l'équipe |
| Coûts / licences | 5 % | Toutes gratuites ; on note surtout le risque de pérennité de l'édition libre |
| **Total** | **100 %** | |

## 3.3 Barème (identique pour tous les critères)

| Note | Signification |
|---|---|
| 5 | Natif, conforme à l'hypothèse, rien à ajouter |
| 4 | Conforme avec un plugin/une config standard |
| 3 | Atteint avec contournement ou dépendance supplémentaire (Redis, service externe…) |
| 2 | Partiellement atteint / écart notable mesuré |
| 1 | Non atteint en édition gratuite |
| 0 | Impossible |

## 3.4 Matrice — résultats mesurés (périmètre : Kong et APISIX)

> Périmètre réduit en cours de lab : seules **Kong OSS 3.9.1** et **APISIX 3.11** ont été mesurées (le sujet impose au moins deux solutions). Traefik et Spring Cloud Gateway restent configurés dans le dépôt (`gateways/traefik`, `gateways/scg`) pour une suite éventuelle, sans note.

| Critère | Poids | Kong /5 | APISIX /5 | Justification (preuves) |
|---|---|---|---|---|
| Routage et politiques | 15 | 4 | 5 | Routage 5/5 pour les deux (E1). Quota : Kong 10,27 req/s et 11,4 par rafale (fenêtre calée sur l'horloge), APISIX exactement 10 req/s et 10 par rafale (E3, `05-rate-limiting.png`). |
| Sécurité / contrôle d'accès | 20 | 3 | 4 | 9/9 cas conformes pour les deux (E2). Kong OSS : clé publique copiée dans la config, pas de JWKS → rotation manuelle ; en-têtes `Server`/`Via`/`X-Kong-*`. APISIX : JWKS natif ; mais messages d'erreur JWT trop détaillés et `Server: APISIX/3.11.0` (E2, E7). CORS plus strict chez APISIX (E7). |
| Débit et latence | 15 | 3 | 5 | Surcoût P95 à 200 req/s : Kong +1,60 ms, APISIX +0,58 ms. À 3 000 req/s : Kong P95 36 ms, CPU 97 % (proche saturation, P99 > 100 ms dès 1 500) ; APISIX P95 1,6 ms, CPU 53 % (E4, graphiques 01, 03, 04). JWT : Kong ≈ 0 ms, APISIX +0,5 ms en P50 (graphique 02). |
| Résilience | 20 | 2 | 5 | Perte d'une instance : 0 erreur pour les deux (graphique 07). Backend en erreur : Kong sans circuit breaker, health check passif qui coupe le backend **sans jamais le réintégrer** (99,9 % d'erreurs, aucune récupération) ; APISIX `api-breaker` : circuit ouvert pendant la panne, refermé < 10 s après (24 % d'erreurs, toutes pendant la panne) (E5, graphique 06). |
| Observabilité | 15 | 5 | 4 | Les deux génèrent un `X-Request-ID` propagé au backend. Kong expose en plus la latence gateway vs upstream dans chaque réponse (`X-Kong-Proxy-Latency`, `X-Kong-Upstream-Latency`) ; APISIX seulement en métriques (E6, partiel). |
| Complexité d'exploitation | 10 | 4 | 3 | Kong DB-less a démarré du premier coup. APISIX : échec au premier démarrage (conflit entre la variable `APISIX_STAND_ALONE` et le `config.yaml` monté), fichier qui doit finir par `#END` (journal). Reconfiguration à chaud (E8) non mesurée. |
| Coûts / licences | 5 | 2 | 5 | Les deux sont gratuits, mais la lignée OSS de Kong s'arrête à la 3.9.x et OIDC/JWKS, quotas avancés sont en édition payante ; APISIX entièrement Apache 2.0 (02-architecture § 2.5, 2.7). |
| **Score pondéré /5** | **100** | **3,30** | **4,45** | `python3 scripts/score.py` |

Lecture : APISIX l'emporte sur les **deux critères les plus lourds** du contexte microservices (résilience, sécurité) et sur la performance. Kong garde l'avantage sur l'observabilité « prête à l'emploi » et la simplicité de mise en route.

## 3.5 Sensibilité

Pondération « performance d'abord » (Débit 30 %, Sécurité 15 %, Résilience 15 %, Routage 12 %, Observabilité 12 %, Exploitation 11 %, Coûts 5 %) : **APISIX 4,51 / Kong 3,27**. Le classement ne change pas.

Test inverse : pour que Kong passe devant, il faudrait que l'observabilité et la simplicité d'exploitation pèsent plus que la résilience et la performance réunies — incohérent avec le contexte microservices retenu.

Recalculer avec une seconde pondération « performance d'abord » (Débit 30 %, Résilience 15 %, Sécurité 15 %, autres inchangés au prorata). Si le classement change, le dire : c'est un argument de soutenance (« la recommandation dépend du contexte »), pas une faiblesse.
