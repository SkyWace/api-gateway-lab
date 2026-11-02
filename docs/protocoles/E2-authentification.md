# E2 — Authentification JWT/OIDC (expérience sécurité)

**Objectif** — Vérifier que `/api/orders` n'est accessible qu'avec un JWT valide émis par Keycloak, et comparer *comment* chaque gateway valide le token.

**Hypothèse**
- Les 4 rejettent les 8 cas invalides en `401` et acceptent le token valide.
- Modes de validation différents : Kong OSS = clé publique **copiée** dans la config (pas de JWKS) ; APISIX = JWKS via discovery OIDC ; SCG = JWKS via Spring Security ; Traefik = délégation à un service externe (`forwardAuth`).
- Conséquence attendue : rotation des clés Keycloak automatique pour APISIX/SCG, **manuelle** pour Kong OSS, dépendante du service externe pour Traefik.

**Environnement** — Realm `lab`, client `lab-client` (client_credentials), clé RSA fixe `identity/keys`.

**Procédure**
1. `docker compose --profile tools run --rm k6 run /scripts/auth.js -e TARGET=<gw>`
2. Relever pour chaque cas le code obtenu et l'en-tête `WWW-Authenticate`.
> Astuce : pour altérer une signature à la main, modifier un caractère au **milieu** — le dernier caractère base64url contient des bits de bourrage ignorés, le token peut rester valide.
3. **Test de rotation** (optionnel, fort en soutenance) : désactiver la clé fixe du realm, puis redemander un token (signé par la clé générée par Keycloak) et rejouer `auth.js`.
   ```bash
   KC="docker compose exec keycloak /opt/keycloak/bin/kcadm.sh"
   $KC config credentials --server http://localhost:8080 --realm master --user admin --password admin
   ID=$($KC get components -r lab -q name=lab-fixed-rsa --fields id --format csv --noquotes)
   $KC update components/$ID -r lab -s 'config.active=["false"]'
   ```
   Réactivation : même commande avec `["true"]`.
4. **Expiration réelle** : passer `accessTokenLifespan` à 60 s dans `identity/realm-lab.json`, recréer Keycloak, attendre 61 s, rejouer le cas « token valide ».

**Mesures** — tableau 9 cas × 4 gateways ; comportement à la rotation ; comportement à l'expiration.

**Résultat** — *à compléter*

| Cas | Attendu | Kong | APISIX | Traefik | SCG |
|---|---|---|---|---|---|
| catalog public sans token | 200 | 200 | 200 | | |
| orders sans token | 401 | 401 | 401 | | |
| orders token valide | 200 | 200 | 200 | | |
| token malformé | 401 | 401 | 401 | | |
| signature altérée | 401 | 401 | 401 | | |
| payload modifié (sub) | 401 | 401 | 401 | | |
| exp modifié | 401 | 401 | 401 | | |
| alg=none | 401 | 401 | 401 | | |
| schéma Basic | 401 | 401 | 401 | | |
| Rotation de clé | accepté sans reconfig | | | | |
| Token réellement expiré | 401 | | | | |

**Observations Kong (02/11/2026, `results/kong-auth.log`)** — 9/9 conformes. Réponse `WWW-Authenticate: Bearer error="invalid_token"` conforme RFC 6750 sur les tokens invalides. NB : k6 compte les 401 attendus dans `http_req_failed` (70 %) — c'est normal, ce n'est pas un taux d'erreur.

**Observations APISIX (02/11, `results/apisix-auth.log`)** — 9/9 conformes, via `openid-connect` + JWKS (aucune clé copiée dans la config). Les 401 portent un `error_description` **très détaillé** (« jwt signature verification failed », « 'exp' claim expired… », « token uses "none" alg… ») : précieux pour déboguer, mais c'est une **fuite d'information** pour un attaquant → à réduire en production.

**Décision** — Les deux protègent correctement (9/9). APISIX est préférable en exploitation : validation par JWKS, donc rotation des clés Keycloak sans reconfiguration, là où Kong OSS exige de recopier la clé publique. Réponse à la question du sujet : **la gateway doit valider elle-même les tokens**, en s'appuyant sur le JWKS de l'IdP plutôt que sur une clé figée. À corriger chez APISIX : la verbosité des messages d'erreur.
