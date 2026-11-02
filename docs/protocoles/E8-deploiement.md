# E8 — Changement de route sans interruption

**Objectif** — Ajouter une route `/api/v2/catalog` pendant un trafic continu, mesurer le délai de prise en compte et vérifier l'absence d'erreurs.

**Hypothèse**
- Kong DB-less : `POST /config` → prise en compte < 1 s, 0 erreur.
- APISIX standalone : fichier relu automatiquement → ~1 s, 0 erreur.
- Traefik : watcher du file provider → ~1–2 s, 0 erreur.
- SCG : routes dans `application.yml` → **redéploiement** nécessaire ; sans 2ᵉ instance, interruption de plusieurs secondes (démarrage JVM). Alternative : routes dynamiques via actuator (non persistantes) ou Spring Cloud Config.

**Procédure**
1. Terminal 1 : `docker compose --profile tools run --rm k6 run /scripts/latency.js -e TARGET=<gw> -e RATE=50 -e DURATION=90s`
2. Terminal 2 : `./scripts/reload.sh <gw>` → délai affiché.
3. Pour SCG : modifier `application.yml`, `time docker compose --profile scg up -d --build scg`, observer les erreurs côté k6.
4. Restaurer la config (commande affichée par le script).

**Mesures** — délai de prise en compte (ms) ; erreurs k6 pendant le changement ; nombre d'étapes manuelles ; traçabilité (le changement est-il dans Git ?).

**Résultat** — *à compléter*

| | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|
| Mécanisme | | | | |
| Délai de prise en compte | | | | |
| Erreurs pendant le changement | | | | |
| Config as code / GitOps | | | | |

**Décision** — *à compléter*.
