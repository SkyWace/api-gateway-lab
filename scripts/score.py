#!/usr/bin/env python3
"""Calcul du score pondéré de la matrice + test de sensibilité.
Remplir NOTES avec les notes /5 issues des expériences (None = pas encore noté)."""

CRITERES = ["Routage", "Securite", "Perf", "Resilience", "Observabilite", "Exploitation", "Couts"]
POIDS = {"Routage": 15, "Securite": 20, "Perf": 15, "Resilience": 20, "Observabilite": 15, "Exploitation": 10, "Couts": 5}
POIDS_PERF = {"Routage": 12, "Securite": 15, "Perf": 30, "Resilience": 15, "Observabilite": 12, "Exploitation": 11, "Couts": 5}

# Notes justifiées dans docs/03-matrice-decision.md (périmètre mesuré : Kong et APISIX)
NOTES = {
    "Kong":   {"Routage": 4, "Securite": 3, "Perf": 3, "Resilience": 2, "Observabilite": 5, "Exploitation": 4, "Couts": 2},
    "APISIX": {"Routage": 5, "Securite": 4, "Perf": 5, "Resilience": 5, "Observabilite": 4, "Exploitation": 3, "Couts": 5},
    # Traefik et SCG : configurés dans le dépôt mais non mesurés (périmètre réduit, cf. note de décision)
    "Traefik": dict.fromkeys(CRITERES),
    "SCG":     dict.fromkeys(CRITERES),
}

def score(notes, poids):
    if any(v is None for v in notes.values()):
        return None
    return sum(poids[c] * notes[c] for c in CRITERES) / 100

for nom, p in [("Pondération contexte", POIDS), ("Pondération performance", POIDS_PERF)]:
    assert sum(p.values()) == 100, f"{nom} : les poids doivent faire 100"
    print(f"\n{nom}")
    res = {g: score(n, p) for g, n in NOTES.items()}
    for g, s in sorted(res.items(), key=lambda x: -(x[1] or -1)):
        print(f"  {g:8s} {'(incomplet)' if s is None else f'{s:.2f} / 5'}")
