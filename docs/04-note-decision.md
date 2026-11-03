# 4. Note de décision — Choix d'une API Gateway pour NordFlux

## Contexte et exigences

NordFlux expose une douzaine de microservices à des clients web, mobiles et internes. Il lui faut un point d'entrée unique qui :
- valide les JWT émis par Keycloak ;
- limite les abus à 10 req/s par client ;
- protège les clients des pannes de backend ;
- permet de suivre une requête de bout en bout.

Pic visé : 1 500 req/s. Cible de production : Kubernetes. Contrainte : les fonctions cœur doivent être disponibles sans licence payante.

## Ce qui a été comparé

**Kong Gateway OSS 3.9.1** et **Apache APISIX 3.11**, en édition gratuite, sur un parcours identique :
- deux API factices (catalogue sur 2 instances, commandes sur 1) ;
- Keycloak et des jeux de données figés ;
- **1 vCPU / 512 Mo par gateway**, limite vérifiée par `docker inspect`.

Sept expériences ont été menées, toutes rejouables (dépôt Git, `results/`, `docs/graphs/`). Traefik et Spring Cloud Gateway sont configurés dans le dépôt mais n'ont pas été mesurés : le périmètre a été réduit à deux solutions, ce que le sujet autorise.

## Résultats marquants

| Expérience | Kong OSS | APISIX |
|---|---|---|
| Routage (E1) | 5/5 | 5/5 |
| Authentification (E2) | 9/9, clé publique statique | 9/9, JWKS |
| Quota 10 req/s (E3) | 10,27 req/s, 11,4 par rafale | 10,00 req/s, 10 par rafale |
| Surcoût P95 à 200 req/s (E4) | +1,60 ms | **+0,58 ms** |
| Coût du JWT, P50 (E4) | ≈ 0 ms | +0,5 ms |
| 3 000 req/s sur 1 vCPU (E4) | 0 erreur, P95 36 ms, CPU 97 % | 0 erreur, **P95 1,6 ms, CPU 53 %** |
| RAM sous charge (E4) | ~205 Mo | **~52 Mo** |
| Perte d'une instance (E5) | 0 erreur | 0 erreur |
| Backend à 50 % d'erreurs (E5) | 26,5 % d'erreurs, retour ≈ 5 s *(avec health check actif ; passif seul : jamais rétabli)* | 24,4 % d'erreurs, retour < 5 s |
| Backend lent / arrêté (E5) | 503 rapides, rétabli < 10 s | non mesuré |
| Corrélation (E6) | `X-Request-ID` + latences dans chaque réponse | `X-Request-ID` |

**La résilience a révélé un piège, pas un écart de produit** (graphique `06-circuit-breaker.png`). Premier run Kong : son health check passif a retiré le backend après 3 erreurs, puis ne l'a **jamais réintégré** — une panne de 30 s devenue une coupure durable. Cause : **notre configuration**, qui n'avait pas de contrôle actif sur cet upstream ; un contrôle passif ne réintègre jamais une cible. Une fois le contrôle actif ajouté, Kong se comporte presque comme le circuit breaker d'APISIX : 503 rapides pendant la panne, retour à la normale en environ 5 s. APISIX y arrive avec un vrai circuit breaker, qui ne dépend pas de la fidélité d'un endpoint `/health`.

![Circuit breaker](graphs/06-circuit-breaker.png)

## Matrice (synthèse)

| | Kong OSS | APISIX |
|---|---|---|
| Critères éliminatoires | aucun déclenché | aucun déclenché |
| Score pondéré (contexte microservices) | 3,70 / 5 | **4,45 / 5** |
| Score pondéré (« performance d'abord ») | 3,57 / 5 | **4,51 / 5** |

Le détail et les justifications sont dans `03-matrice-decision.md`. Le classement est stable sur les deux pondérations testées, mais l'écart s'est réduit après correction de la config Kong (3,30 → 3,70) : le choix reste sensible au contexte.

## Recommandation

**Apache APISIX** pour NordFlux.

À résilience comparable, trois écarts mesurés le départagent :
- **la marge sous charge** : à 3 000 req/s sur 1 vCPU, P95 de 1,6 ms et 53 % de CPU, contre 36 ms et 97 % pour Kong ;
- **la sécurité opérationnelle** : la validation JWKS suit la rotation des clés Keycloak sans reconfiguration ;
- **la pérennité** : tout ce qui a été utilisé est en Apache 2.0, alors que la lignée OSS de Kong est gelée en 3.9.x.

Il offre en plus un vrai circuit breaker, plus robuste qu'un retour basé sur `/health`, et un quota tenu exactement.

**Conditions de mise en œuvre :**
- réduire les messages d'erreur JWT, qui révèlent la cause du refus à un éventuel attaquant ;
- masquer l'en-tête `Server` ;
- passer le rate limiting sur Redis dès qu'il y a plus d'une instance de gateway, sinon le quota est multiplié par le nombre d'instances ;
- en production, déployer avec etcd ou l'Ingress Controller plutôt qu'en mode standalone.

**Quand Kong resterait pertinent.** Kong OSS reste solide sur le routage, le failover et surtout l'observabilité prête à l'emploi : la latence gateway et la latence backend sont visibles dans chaque réponse. Il conviendrait à une équipe qui privilégie l'observabilité sans outillage et la simplicité de démarrage, avec des volumes modérés. Deux réserves s'appliqueraient :
- ajouter **systématiquement** un health check actif sur chaque upstream ;
- tenir compte du gel de la lignée OSS à la 3.9.x : OIDC/JWKS et les quotas avancés sont en édition payante.

## Compromis assumés

- **APISIX valide les tokens un peu plus lentement** (+0,5 ms en médiane), c'est le prix du JWKS. C'est négligeable devant le gain de sécurité opérationnelle.
- **APISIX a été plus délicat à démarrer** (incident de configuration au premier lancement). Il demande un peu plus de maîtrise de la configuration.

## Limites de validité

- **Mesures sur un poste de développement** (MacBook Air sous Docker Desktop), sans TLS, avec une seule instance de gateway : les résultats valent **en relatif**, pas comme dimensionnement de production.
- **Incidents de protocole détectés et corrigés en cours de route :**
  1. la limite CPU était ignorée par Docker Desktop macOS : mesures de performance rejouées avec `deploy.resources`, puis vérifiées ;
  2. le générateur k6 saturait en allouant ses utilisateurs virtuels : 600 pré-alloués ;
  3. bruit de l'hôte : runs avec requêtes perdues rejoués, médiane de 3 runs ;
  4. un bug du script de latence sur la route protégée, corrigé.
- **Écart de configuration non neutralisé :** Kong avait davantage de métriques Prometheus actives qu'APISIX. Une partie de l'écart de CPU peut en venir.
- **Expériences non réalisées :** déploiement à chaud (E8), capture Prometheus (E6, partielle), scénarios backend lent et arrêt complet de orders pour APISIX, haute disponibilité et Kubernetes.

## Prochaines étapes

1. Rejouer E3 et E5 sur un cluster Kubernetes de test, avec 2 instances d'APISIX et le rate limiting sur Redis.
2. Mesurer E8 (changement de route sans interruption) et activer le tracing OpenTelemetry de bout en bout.
3. Rejouer le débit de Kong avec des métriques Prometheus allégées, pour savoir quelle part de l'écart de CPU vient de la configuration.
