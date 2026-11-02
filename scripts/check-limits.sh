#!/usr/bin/env bash
# Vérifie que les limites CPU/RAM sont réellement appliquées aux conteneurs lancés.
# Attendu gateway : 1.00 CPU / 512 Mo ; backends : 0.50 CPU / 256 Mo.
cd "$(dirname "$0")/.."
printf "%-28s %8s %10s\n" CONTENEUR CPU "RAM (Mo)"
for id in $(docker compose ps -q); do
  docker inspect -f '{{.Name}} {{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}' "$id" |
    awk '{ cpu = ($2 == 0) ? "AUCUNE" : sprintf("%.2f", $2/1e9);
           ram = ($3 == 0) ? "AUCUNE" : sprintf("%d", $3/1048576);
           printf "%-28s %8s %10s\n", substr($1,2), cpu, ram }'
done
