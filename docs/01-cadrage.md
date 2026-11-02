# 1. Cadrage — contexte « Microservices »

## 1.1 Situation

**NordFlux** (entreprise fictive) édite une plateforme de gestion de commandes industrielles découpée en une douzaine de microservices (catalogue produits, commandes, stocks, facturation, expédition…). Aujourd'hui, chaque service est exposé directement : chaque équipe réimplémente l'authentification, les logs et la gestion d'erreurs, et les clients connaissent l'adresse de chaque service.

L'entreprise veut **un point d'entrée unique** devant ses services, qui porte les préoccupations transverses : routage, contrôle d'accès, limitation des abus, résilience face aux pannes de backend et observabilité de bout en bout.

**Question centrale** : quelle gateway répond le mieux à ces contraintes, et comment le démontrer par des mesures reproductibles ?

## 1.2 Acteurs

| Acteur | Rôle | Accès |
|---|---|---|
| Front web (SPA) | Interface des commerciaux et clients | Navigateur → gateway (CORS nécessaire) |
| Application mobile | Suivi de commandes terrain | Mobile → gateway (JWT utilisateur) |
| Services internes / batchs | Synchronisation ERP, reporting | Service → gateway (JWT client_credentials) |
| Fournisseur d'identité | Émet et signe les tokens (Keycloak, OIDC) | Interrogé par la gateway (JWKS) |
| Équipe plateforme / Ops | Exploite la gateway, déploie les routes | Config as code, métriques, logs |

## 1.3 Flux retenus pour le POC

Deux services représentatifs, servis par une API factice identique :

| Flux | Route | Exposition | Politiques |
|---|---|---|---|
| Consultation catalogue | `GET /api/catalog`, `GET /api/catalog/{id}` | Publique | Rate limiting par client (`X-Client-Id`), CORS, répartition sur **2 instances** |
| Commandes | `GET/POST /api/orders[/{id}]` | Protégée | JWT obligatoire (émis par Keycloak), timeout, retries, circuit breaker si disponible, **1 instance** |

Les endpoints techniques des backends (`/admin/chaos`, `/health`) ne doivent **jamais** être exposés par la gateway.

## 1.4 Contraintes de sécurité

- Validation du JWT à la gateway : signature (RS256, clé publique du realm), `exp`, `iss`. Un token altéré, expiré, `alg=none` ou absent → `401`.
- Pas de secret ni de token dans les URL (en-tête `Authorization` uniquement).
- CORS restreint à l'origine du front (`http://localhost:5173` dans le POC).
- Les en-têtes de réponse ne doivent pas divulguer d'informations inutiles (version du produit, topologie interne).
- Requêtes malformées (path traversal, en-têtes géants, JSON invalide) rejetées proprement, sans contourner le contrôle d'accès.
- TLS : terminé à la gateway en production ; **hors périmètre mesuré** dans le POC (même conditions pour les 4 solutions, à signaler comme limite).

## 1.5 Volumes (hypothèses de dimensionnement)

| Indicateur | Valeur retenue |
|---|---|
| Trafic moyen | ~200 req/s |
| Pic (campagnes, fin de mois) | ~1 500 req/s |
| Quota par client | 10 req/s sur le catalogue public |
| Taille moyenne de réponse | 0,5 à 5 Ko (JSON) |

## 1.6 Critères de succès

| # | Critère | Seuil |
|---|---|---|
| S1 | Routage correct des 2 services, 404 propre sinon | 100 % des cas du smoke test |
| S2 | Contrôle d'accès JWT conforme | 9/9 cas de `auth.js` |
| S3 | Surcoût de latence de la gateway | P95 < +10 ms vs baseline à 200 req/s |
| S4 | Tenue en charge | ≥ 1 500 req/s sans erreur, avec 1 vCPU / 512 Mo |
| S5 | Quotas | Client gourmand limité à ≈ 10 req/s ; client raisonnable jamais limité |
| S6 | Résilience | Perte d'une instance catalogue : < 1 % d'erreurs visibles ; backend lent : réponse en ≤ 5 s |
| S7 | Observabilité | Métriques Prometheus + identifiant de corrélation propagé jusqu'au backend |
| S8 | Exploitation | Configuration déclarative versionnable ; changement de route sans interruption |

## 1.7 Critères éliminatoires

Un critère éliminatoire écarte la solution **quel que soit son score global** :

- **E1** — Validation JWT et rate limiting impossibles sans licence payante.
- **E2** — Configuration non versionnable dans Git (clic-ops uniquement).
- **E3** — Pas d'export de métriques exploitable par Prometheus.
- **E4** — Pas de déploiement possible sur Kubernetes (cible de production de NordFlux).

## 1.8 Solutions candidates et périmètre

| Solution | Version | Édition | Mode de déploiement POC | Rôle dans l'étude |
|---|---|---|---|---|
| Kong Gateway | 3.9.1 | OSS (Apache 2.0) | DB-less, config déclarative | Gateway « à plugins », référence du marché |
| Apache APISIX | 3.11.0 | Open source (Apache 2.0) | Standalone YAML (sans etcd) | Gateway dynamique, alternative à Kong |
| Traefik Proxy | v3.3 | OSS (MIT) | File provider | Reverse proxy cloud-native avec middlewares |
| Spring Cloud Gateway | 4.2 (Spring Cloud 2024.0.1, Boot 3.4.5) | Open source (Apache 2.0) | Application Java packagée | Gateway applicative (écosystème Java de l'équipe) |

> **Périmètre effectivement mesuré :** Kong et APISIX. Traefik et Spring Cloud Gateway ont été configurés mais pas mesurés (réduction de périmètre en cours de lab ; le sujet impose au moins deux solutions).

Toutes les fonctionnalités utilisées appartiennent à l'édition **gratuite**. Quand une fonctionnalité n'existe qu'en édition payante, elle est **signalée et non utilisée** (voir `02-architecture.md` § 2.5).
