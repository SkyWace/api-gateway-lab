# Graphiques

Générés par `python3 scripts/graphs.py` à partir des fichiers de `results/`.

## Latence P50/P95/P99 à 200 req/s

![Latence P50/P95/P99 à 200 req/s](01-latence.png)

## Coût de la validation JWT

![Coût de la validation JWT](02-cout-jwt.png)

## Latence P95 par palier de charge

![Latence P95 par palier de charge](03-debit-p95-paliers.png)

## CPU et RAM pendant la montée en charge

![CPU et RAM pendant la montée en charge](04-cpu-ram.png)

## Rate limiting par client

![Rate limiting par client](05-rate-limiting.png)

## Backend en erreur (50 % de 500) : ce que voit le client

![Backend en erreur (50 % de 500) : ce que voit le client](06-circuit-breaker.png)

## Failover lors de la perte d'une instance

![Failover lors de la perte d'une instance](07-failover-catalogue.png)

