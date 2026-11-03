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
| Résilience | 20 | 4 | 5 | Perte d'une instance : 0 erreur pour les deux (graphique 07). Backend à 50 % d'erreurs, **avec health checks actif + passif** : Kong exclut puis réintègre la cible, retour à 100 % de 200 ≈ 5 s après la panne (26,5 % d'erreurs sur le run, 40 × 500 transmis au client) ; APISIX `api-breaker` : même profil (24,4 % d'erreurs, 24 × 500). Écart restant pour Kong : pas de vrai circuit breaker (la réintégration dépend d'un `/health` qui reflète l'état réel) et un piège de config (passif seul = jamais réintégré, run initial). Backend lent / arrêté : Kong coupe en 503 et se rétablit < 10 s (E5, graphique 06). |
| Observabilité | 15 | 5 | 4 | Les deux génèrent un `X-Request-ID` propagé au backend. Kong expose en plus la latence gateway vs upstream dans chaque réponse (`X-Kong-Proxy-Latency`, `X-Kong-Upstream-Latency`) ; APISIX seulement en métriques (E6, partiel). |
| Complexité d'exploitation | 10 | 4 | 3 | Kong DB-less a démarré du premier coup. APISIX : échec au premier démarrage (conflit entre la variable `APISIX_STAND_ALONE` et le `config.yaml` monté), fichier qui doit finir par `#END` (journal). Reconfiguration à chaud (E8) non mesurée. |
| Coûts / licences | 5 | 2 | 5 | Les deux sont gratuits, mais la lignée OSS de Kong s'arrête à la 3.9.x et OIDC/JWKS, quotas avancés sont en édition payante ; APISIX entièrement Apache 2.0 (02-architecture § 2.5, 2.7). |
| **Score pondéré /5** | **100** | **3,70** | **4,45** | `python3 scripts/score.py` |

Lecture : une fois Kong correctement configuré, la **résilience ne départage presque plus** les deux solutions. APISIX garde l'avantage sur la **performance sous charge**, la **sécurité opérationnelle** (JWKS) et les **licences** ; Kong sur l'observabilité « prête à l'emploi » et la simplicité de mise en route.

*Historique : avant correction de la config Kong (passif seul), la note résilience de Kong était 2 et son score 3,30.*

## 3.5 Sensibilité

Pondération « performance d'abord » (Débit 30 %, Sécurité 15 %, Résilience 15 %, Routage 12 %, Observabilité 12 %, Exploitation 11 %, Coûts 5 %) : **APISIX 4,51 / Kong 3,57**. Le classement ne change pas.

Test inverse : avec la résilience désormais proche, Kong passerait devant si l'**observabilité et l'exploitation** pesaient nettement plus que la **performance et les licences** (par ex. Observabilité 30 %, Exploitation 25 %, Débit 5 %, Coûts 0 %). Ce n'est pas le contexte retenu, mais l'écart est assez réduit pour que le choix soit **sensible au contexte** — argument à assumer en soutenance.

Recalculer avec une seconde pondération « performance d'abord » (Débit 30 %, Résilience 15 %, Sécurité 15 %, autres inchangés au prorata). Si le classement change, le dire : c'est un argument de soutenance (« la recommandation dépend du contexte »), pas une faiblesse.
