# 4. Note de décision — Choix d'une API Gateway pour NordFlux

> **Statut : brouillon.** Les passages entre crochets `[…]` sont à remplacer par les mesures réelles (E1–E8). La recommandation ci-dessous est l'**hypothèse issue de l'étude documentaire et de la conception du POC** ; elle doit être confirmée ou infirmée par les résultats. Si les mesures la contredisent, c'est la mesure qui gagne. Viser 1 à 2 pages une fois complétée.

## Contexte et exigences

NordFlux expose une douzaine de microservices à des clients web, mobiles et internes. Le besoin : un point d'entrée unique qui valide les JWT émis par Keycloak, limite les abus par client (10 req/s), protège les clients des pannes de backend et permet de suivre une requête de bout en bout. Pic visé : 1 500 req/s. Cible de production : Kubernetes. Contrainte : fonctions cœur sans licence payante.

## Ce qui a été comparé

Quatre solutions en édition gratuite — Kong Gateway OSS 3.9.1, Apache APISIX 3.11, Traefik Proxy v3.3, Spring Cloud Gateway 4.2 — sur un parcours identique (2 API factices, Keycloak, mêmes données, 1 vCPU / 512 Mo par gateway), au travers de 8 expériences : routage, authentification, rate limiting, latence/débit, résilience, observabilité, sécurité des entrées, déploiement à chaud.

## Résultats marquants

- **Sécurité** — Kong et APISIX : 8/8 tokens invalides rejetés en 401 (APISIX détaille trop la cause de l'erreur) ; Traefik [ ], SCG [ ]. Kong OSS ne lit pas le JWKS : la clé publique est copiée dans sa configuration, donc [la rotation de clé a cassé l'accès / a nécessité une reconfiguration]. Traefik OSS ne valide pas de JWT : il a fallu écrire un service de validation externe.
- **Performance** — surcoût P95 à 200 req/s (1 vCPU) : Kong +1,6 ms, APISIX +0,6 ms, Traefik [x] ms, SCG [x] ms. Débit : Kong sert 3 000 req/s sans erreur mais CPU à 97 % et P99 > 100 ms dès 1 500 req/s ; APISIX 3 000 req/s à 53 % CPU, P95 1,6 ms ; Traefik [ ], SCG [ ].
- **Quotas** — même réglage, comportements différents : fenêtre fixe (Kong, APISIX) vs token bucket (Traefik, SCG). Kong : client gourmand tenu à 10,27 req/s (+2,7 %), aucun refus pour le client raisonnable, ~11,4 requêtes acceptées par rafale (effet fenêtre fixe) , APISIX exactement 10 req/s et 10 par rafale ; [Traefik, SCG]. Seul SCG partage ses compteurs (Redis) ; les autres comptent par instance, donc un quota de 10 req/s devient 20 req/s avec 2 instances de gateway.
- **Résilience** — perte d'une instance catalogue : Kong 0 % d'erreur (retries + health checks, réintégration ≈ 5 s) ; APISIX identique. Backend en erreur : Kong OSS n'a pas de circuit breaker ; son health check passif a coupé le backend après 3 erreurs… **sans jamais le réintégrer** (503 pendant toute la suite du test, 30 s de panne réelle). APISIX : circuit ouvert pendant la panne puis refermé en < 10 s (24 % d'erreurs, toutes pendant la panne). Traefik, SCG : [ ].
- **Observabilité** — corrélation native chez Kong et APISIX, ajoutée par un filtre chez SCG, absente chez Traefik sans tracing.
- **Exploitation** — changement de route sans interruption en [x] s pour Kong, APISIX et Traefik ; redéploiement avec [x] s d'indisponibilité pour SCG.

## Matrice (synthèse)

| | Kong OSS | APISIX | Traefik | SCG |
|---|---|---|---|---|
| Éliminatoires | [ ] | [ ] | [ ] | [ ] |
| Score pondéré /5 | [ ] | [ ] | [ ] | [ ] |
| Score pondération « performance » /5 | [ ] | [ ] | [ ] | [ ] |

## Recommandation

**Hypothèse de recommandation : Apache APISIX** comme gateway de NordFlux, déployée en mode Kubernetes (Ingress Controller ou etcd + plusieurs instances), avec le rate limiting adossé à Redis dès qu'on dépasse une instance.

Pourquoi (à étayer par les mesures) : c'est la seule des quatre qui couvre **en édition gratuite et sans code** les deux problématiques prioritaires du contexte — résilience (circuit breaker natif) et observabilité (request-id, Prometheus) — tout en validant les tokens via JWKS, donc en suivant la rotation des clés Keycloak.

**Alternatives selon le contexte** — aucune solution n'est la meilleure dans l'absolu :
- **Spring Cloud Gateway** si l'équipe est 100 % Java/Spring et les volumes modérés : intégration Spring Security/Resilience4j excellente, extensibilité par le code ; en contrepartie, empreinte JVM, Redis obligatoire pour les quotas et redéploiement pour changer une route.
- **Traefik** comme **ingress** Kubernetes (TLS, ACME, découverte automatique), éventuellement *devant* une gateway : en OSS il lui manque la validation JWT et la corrélation.
- **Kong OSS** reste techniquement solide, mais la lignée open source est figée en 3.9.x et les fonctions attendues ici (OIDC/JWKS, quotas avancés) sont en édition payante : risque de pérennité / de coût à moyen terme.

## Compromis et limites

- Mesures sur poste de développement sous Docker, sans TLS, une seule instance de gateway : résultats valables en **relatif**, pas comme dimensionnement de production.
- Haute disponibilité et Kubernetes non testés : la question des quotas partagés (Redis) et de la configuration (etcd pour APISIX, CRD pour Traefik/Kong) reste à valider sur un cluster.
- Fonctions des éditions payantes volontairement exclues ; une évaluation Kong Enterprise / Traefik Hub changerait la comparaison.
- Incidents de protocole, détectés et corrigés : (1) limite CPU ignorée par Docker Desktop macOS (clé `cpus:`) → mesures de perf Kong rejouées avec `deploy.resources` et vérification `check-limits.sh` ; (2) générateur k6 saturant pendant l'allocation de VU → 600 VU pré-alloués ; (3) bruit de l'hôte (MacBook Air, refroidissement passif) → runs avec `dropped_iterations` rejoués, médiane de 3 runs.

## Prochaines étapes

1. Rejouer E3 et E5 sur un cluster Kubernetes de test avec 2 instances de la gateway retenue.
2. Activer le tracing OpenTelemetry de bout en bout.
3. Mettre la configuration de la gateway sous pipeline GitOps (revue, validation, déploiement).
