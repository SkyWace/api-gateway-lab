#!/usr/bin/env bash
# Échantillonne CPU/RAM d'un conteneur toutes les secondes -> results/<cible>-stats-<date>.csv
# Usage : ./scripts/stats.sh kong   (Ctrl+C pour arrêter)
set -euo pipefail
cd "$(dirname "$0")/.."
SVC=${1:?service (kong|apisix|traefik|scg)}
CID=$(docker compose ps -q "$SVC")
OUT="results/${SVC}-stats-$(date +%Y%m%d-%H%M%S).csv"
echo "timestamp;cpu_percent;mem_usage" > "$OUT"
echo "Écriture dans $OUT (Ctrl+C pour arrêter)"
while true; do
  docker stats --no-stream --format "{{.CPUPerc}};{{.MemUsage}}" "$CID" | sed "s/^/$(date +%s);/" >> "$OUT"
  sleep 1
done
