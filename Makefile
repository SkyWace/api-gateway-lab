# Raccourcis : make up GW=kong | make smoke GW=kong | make k6 GW=kong T=latency | make down GW=kong
GW ?= kong
T ?= latency
up:    ; docker compose --profile $(GW) up -d --build
down:  ; docker compose --profile $(GW) down
smoke: ; ./scripts/smoke.sh $(GW)
k6:    ; docker compose --profile tools run --rm k6 run /scripts/$(T).js -e TARGET=$(GW)
logs:  ; docker compose --profile $(GW) logs -f $(GW)
score: ; python3 scripts/score.py
.PHONY: up down smoke k6 logs score
