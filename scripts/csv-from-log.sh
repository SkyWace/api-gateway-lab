#!/usr/bin/env bash
# Extrait la série temporelle de resilience.js depuis la sortie k6.
# Usage : docker compose --profile tools run --rm k6 run ... 2>&1 | tee results/run.log
#         ./scripts/csv-from-log.sh results/run.log > results/kong-resilience.csv
set -euo pipefail
echo "t_ms;status;duration_ms;instance"
grep -o 'CSV;[^"]*' "${1:?fichier log}" | sed 's/^CSV;//'
