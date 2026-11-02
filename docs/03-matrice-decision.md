# 3. Matrice de décision

## 3.1 Critères éliminatoires (vérifiés avant tout score)

| Critère | Kong OSS | APISIX | Traefik OSS | SCG | Preuve |
|---|---|---|---|---|---|
| E1 — JWT + rate limiting sans licence | ☐ | ☐ | ☐ | ☐ | E2, E3 |
| E2 — Config versionnable dans Git | ☐ | ☐ | ☐ | ☐ | dépôt, E8 |
| E3 — Métriques Prometheus | ☐ | ☐ | ☐ | ☐ | E6 |
| E4 — Déployable sur Kubernetes | ☐ | ☐ | ☐ | ☐ | doc officielle (Ingress Controller / Helm) |

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

## 3.4 Matrice — *à remplir avec les résultats réels*

| Critère | Poids | Kong /5 | APISIX /5 | Traefik /5 | SCG /5 | Justification (citer E1…E8 et les fichiers de `results/`) |
|---|---|---|---|---|---|---|
| Routage et politiques | 15 | | | | | E1, E8 |
| Sécurité / contrôle d'accès | 20 | | | | | E2, E7 |
| Débit et latence | 15 | | | | | E4 |
| Résilience | 20 | | | | | E5 |
| Observabilité | 15 | | | | | E6 |
| Complexité d'exploitation | 10 | | | | | E1, E8 |
| Coûts / licences | 5 | | | | | 02-architecture § 2.5 et 2.7 |
| **Score pondéré /5** | | | | | | Σ(poids × note) / 100 |

Calcul : `python3 scripts/score.py` (éditer les notes en tête du script).

## 3.5 Sensibilité

Recalculer avec une seconde pondération « performance d'abord » (Débit 30 %, Résilience 15 %, Sécurité 15 %, autres inchangés au prorata). Si le classement change, le dire : c'est un argument de soutenance (« la recommandation dépend du contexte »), pas une faiblesse.
