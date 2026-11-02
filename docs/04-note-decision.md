# 4. Note de décision — Choix d'une API Gateway pour NordFlux

> **Statut : brouillon.** Les passages entre crochets `[…]` sont à remplacer par les mesures réelles (E1–E8). La recommandation ci-dessous est l'**hypothèse issue de l'étude documentaire et de la conception du POC** ; elle doit être confirmée ou infirmée par les résultats. Si les mesures la contredisent, c'est la mesure qui gagne. Viser 1 à 2 pages une fois complétée.

## Contexte et exigences

NordFlux expose une douzaine de microservices à des clients web, mobiles et internes. Le besoin : un point d'entrée unique qui valide les JWT émis par Keycloak, limite les abus par client (10 req/s), protège les clients des pannes de backend et permet de suivre une requête de bout en bout. Pic visé : 1 500 req/s. Cible de production : Kubernetes. Contrainte : fonctions cœur sans licence payante.

## Ce qui a été comparé

Quatre solutions en édition gratuite — Kong Gateway OSS 3.9.1, Apache APISIX 3.11, Traefik Proxy v3.3, Spring Cloud Gateway 4.2 — sur un parcours identique (2 API factices, Keycloak, mêmes données, 1 vCPU / 512 Mo par gateway), au travers de 8 expériences : routage, authentification, rate limiting, latence/débit, résilience, observabilité, sécurité des entrées, déploiement à chaud.

## Résultats marquants

- **Sécurité** — [les 4 rejettent / X rejette… les 8 cas de token invalide]. Kong OSS ne lit pas le JWKS : la clé publique est copiée dans sa configuration, donc [la rotation de clé a cassé l'accès / a nécessité une reconfiguration]. Traefik OSS ne valide pas de JWT : il a fallu écrire un service de validation externe.
- **Performance** — surcoût P95 à 200 req/s : Kong [x] ms, APISIX [x] ms, Traefik [x] ms, SCG [x] ms. Débit max soutenu : [x / x / x / x] req/s. [Toutes / X ne] dépassent le pic visé de 1 500 req/s.
- **Quotas** — même réglage, comportements différents : fenêtre fixe (Kong, APISIX) vs token bucket (Traefik, SCG). [Écart mesuré au quota]. Seul SCG partage ses compteurs (Redis) ; les autres comptent par instance, donc un quota de 10 req/s devient 20 req/s avec 2 instances de gateway.
- **Résilience** — perte d'une instance : [x %] d'erreurs. Backend en erreur : APISIX, Traefik et SCG ont ouvert le circuit [en x s] ; Kong OSS, sans circuit breaker, a [relayé les 500 au client].
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
- [Incidents rencontrés pendant les tests et leur impact sur la confiance dans les chiffres.]

## Prochaines étapes

1. Rejouer E3 et E5 sur un cluster Kubernetes de test avec 2 instances de la gateway retenue.
2. Activer le tracing OpenTelemetry de bout en bout.
3. Mettre la configuration de la gateway sous pipeline GitOps (revue, validation, déploiement).
