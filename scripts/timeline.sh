#!/usr/bin/env bash
# Chronologie d'un run resilience.js : nombre de réponses par statut, par tranche de N secondes.
# Usage : ./scripts/timeline.sh results/apisix-errors-orders.log [10]
set -euo pipefail
LOG=${1:?fichier log}; STEP=${2:-10}
echo "tranche(s) statut nombre"
grep -o 'CSV;[^"]*' "$LOG" | sed 's/^CSV;//' | sort -t';' -k1 -n |
  awk -F';' -v step="$STEP" 'NR==1{s=$1} {t=int(($1-s)/(step*1000))*step; c[t";"$2]++}
       END{for(k in c){split(k,a,";"); printf "%4d-%-4d %s %d\n", a[1], a[1]+step, a[2], c[k]}}' | sort -n
