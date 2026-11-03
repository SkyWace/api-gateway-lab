#!/usr/bin/env python3
"""Génère les graphiques du lab à partir des VRAIS fichiers de results/ (aucune valeur saisie à la main).

Usage : python3 scripts/graphs.py            -> PNG dans docs/graphs/
Dépendance : matplotlib (pip install matplotlib)

Chaque graphique est sauté proprement si les logs nécessaires sont absents.
"""
import csv
import glob
import os
import re
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "docs", "graphs")
os.makedirs(OUT, exist_ok=True)

GATEWAYS = ["kong", "apisix", "traefik", "scg"]
LABEL = {"direct": "Direct (sans gateway)", "kong": "Kong OSS 3.9", "apisix": "APISIX 3.11",
         "traefik": "Traefik v3.3", "scg": "Spring Cloud Gateway"}
# Palette catégorielle de référence (ordre fixe, validée CVD) ; "direct" = neutre
COLOR = {"direct": "#8c8b86", "kong": "#2a78d6", "apisix": "#eb6834", "traefik": "#1baf7a", "scg": "#6250d6"}
# Couleurs de statut réservées (toujours accompagnées d'un libellé)
STATUS = {"200": ("#0ca30c", "200 OK"), "500": ("#d03b3b", "500 renvoyé par le backend"),
          "503": ("#ec835a", "503 généré par la gateway"), "502": ("#fab219", "502"), "504": ("#fab219", "504")}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold", "legend.frameon": False,
})

ANSI = re.compile(r"\x1b\[[0-9;]*m")
generated = []


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return ANSI.sub("", f.read())


def to_ms(v):
    m = re.match(r"([\d.]+)(µs|us|ms|s|m)?", v)
    n, u = float(m.group(1)), m.group(2) or "ms"
    return {"µs": n / 1000, "us": n / 1000, "ms": n, "s": n * 1000, "m": n * 60000}[u]


def durations(line):
    """Extrait med / p(95) / p(99) d'une ligne de Trend k6."""
    out = {}
    for key, name in (("med", "p50"), ("p\\(95\\)", "p95"), ("p\\(99\\)", "p99")):
        m = re.search(rf"\b{key}=([\d.]+(?:µs|us|ms|s|m)?)", line)
        if m:
            out[name] = to_ms(m.group(1))
    return out


def main_duration(path):
    for line in read(path).splitlines():
        if re.match(r"\s*http_req_duration\.", line):
            return durations(line)
    return None


def save(fig, name, title):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    generated.append((name, title))
    print("  ✓", name)


def present(gws, pattern):
    return [g for g in gws if glob.glob(os.path.join(RES, pattern.format(g=g)))]


# ---------------------------------------------------------------- 1. Latence
def chart_latency():
    targets = [t for t in ["direct"] + GATEWAYS if glob.glob(os.path.join(RES, f"{t}-latency-[123].log"))]
    if len(targets) < 2:
        return
    stats = {}
    for t in targets:
        runs = [d for d in (main_duration(p) for p in sorted(glob.glob(os.path.join(RES, f"{t}-latency-[123].log")))) if d]
        stats[t] = {k: statistics.median(r[k] for r in runs) for k in ("p50", "p95", "p99")}
    fig, ax = plt.subplots(figsize=(8, 4.2))
    groups, width = ["P50", "P95", "P99"], 0.8 / len(targets)
    for i, t in enumerate(targets):
        xs = [g + (i - (len(targets) - 1) / 2) * width for g in range(3)]
        vals = [stats[t][k] for k in ("p50", "p95", "p99")]
        bars = ax.bar(xs, vals, width - 0.04, color=COLOR[t], label=LABEL[t])
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:.2f}".replace(".", ","), (b.get_x() + b.get_width() / 2, v),
                        ha="center", va="bottom", fontsize=8, color=INK2, xytext=(0, 2), textcoords="offset points")
    ax.set_xticks(range(3), groups)
    ax.set_ylabel("Latence (ms)")
    ax.set_title("Latence à 200 req/s — route publique /api/catalog")
    ax.legend(loc="upper left")
    fig.text(0.01, -0.02, "Médiane de 3 runs de 60 s, 1 vCPU / 512 Mo par gateway. Source : results/*-latency-[123].log",
             fontsize=8, color=INK2)
    save(fig, "01-latence.png", "Latence P50/P95/P99 à 200 req/s")


# ---------------------------------------------------------------- 2. Surcoût JWT
def chart_jwt():
    gws = [g for g in GATEWAYS if glob.glob(os.path.join(RES, f"{g}-latency-orders.log"))
           and glob.glob(os.path.join(RES, f"{g}-latency-[123].log"))]
    if not gws:
        return
    fig, ax = plt.subplots(figsize=(7, 3.6))
    width = 0.36
    for i, g in enumerate(gws):
        cat = statistics.median(main_duration(p)["p50"] for p in glob.glob(os.path.join(RES, f"{g}-latency-[123].log")))
        orders = main_duration(os.path.join(RES, f"{g}-latency-orders.log"))["p50"]
        for j, (v, lab) in enumerate(((cat, "publique (sans token)"), (orders, "protégée (JWT)"))):
            b = ax.bar(i + (j - 0.5) * width, v, width - 0.04, color=COLOR[g], alpha=1.0 if j else 0.45,
                       hatch=None if j else "//", edgecolor=SURFACE)
            ax.annotate(f"{lab}\n{v:.2f} ms".replace(".", ","), (i + (j - 0.5) * width, v), ha="center",
                        va="bottom", fontsize=8, color=INK2, xytext=(0, 2), textcoords="offset points")
    ax.set_xticks(range(len(gws)), [LABEL[g] for g in gws])
    ax.set_ylabel("Latence médiane P50 (ms)")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.25)
    ax.set_title("Coût de la validation du token (P50, 200 req/s)")
    fig.text(0.01, -0.03, "Kong : plugin jwt (clé publique statique) · APISIX : openid-connect (JWKS). Source : *-latency-*.log",
             fontsize=8, color=INK2)
    save(fig, "02-cout-jwt.png", "Coût de la validation JWT")


# ---------------------------------------------------------------- 3. Débit par palier
def paliers(path):
    """Renvoie {palier: {p95, served}} depuis le résumé throughput.js."""
    res, section = defaultdict(dict), None
    for line in read(path).splitlines():
        m = re.match(r"\s*(http_req_duration|http_reqs|http_req_failed)\.", line)
        if m:
            section = m.group(1)
            continue
        if re.match(r"\s*[a-z_]+\.{3,}", line):
            section = None
        pm = re.search(r"\{ palier:(\d+) \}\.+:\s*(.*)", line)
        if pm and section:
            p = int(pm.group(1))
            if section == "http_req_duration":
                res[p].update(durations(pm.group(2)))
            elif section == "http_reqs":
                res[p]["served"] = int(pm.group(2).split()[0])
    return dict(res)


def chart_throughput():
    gws = present(GATEWAYS, "{g}-throughput.log")
    data = {g: paliers(os.path.join(RES, f"{g}-throughput.log")) for g in gws}
    data = {g: d for g, d in data.items() if d}
    if not data:
        return
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for g, d in data.items():
        xs = sorted(d)
        ax.plot(xs, [d[x]["p95"] for x in xs], color=COLOR[g], lw=2, marker="o", ms=7,
                markeredgecolor=SURFACE, markeredgewidth=2, label=f"{LABEL[g]} — P95")
        last = xs[-1]
        ax.annotate(f"{d[last]['p95']:.1f} ms".replace(".", ","), (last, d[last]["p95"]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK2)
    ax.set_yscale("log")
    ax.set_xlabel("Charge visée (req/s)")
    ax.set_ylabel("Latence P95 (ms, échelle log)")
    ax.set_xticks(sorted(next(iter(data.values()))))
    ax.set_title("Montée en charge : latence P95 par palier")
    ax.legend(loc="upper left")
    fig.text(0.01, -0.06, "0 erreur à tous les paliers pour toutes les gateways. 1 vCPU / 512 Mo. Source : results/*-throughput.log",
             fontsize=8, color=INK2)
    save(fig, "03-debit-p95-paliers.png", "Latence P95 par palier de charge")


# ---------------------------------------------------------------- 4. CPU / RAM
def latest_stats(g):
    files = sorted(glob.glob(os.path.join(RES, f"{g}-stats-*.csv")))
    return files[-1] if files else None


def load_stats(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.reader(f, delimiter=";"):
            if len(r) < 3 or not r[0].isdigit():
                continue
            cpu = float(r[1].rstrip("%").replace(",", "."))
            mem = re.match(r"([\d.]+)\s*([KMG]i?B)", r[2])
            mb = float(mem.group(1)) * {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024, "kB": 1 / 1000, "MB": 1, "GB": 1000}.get(mem.group(2), 1)
            rows.append((int(r[0]), cpu, mb))
    rows.sort()
    return rows


def chart_resources():
    gws = [g for g in GATEWAYS if latest_stats(g)]
    if not gws:
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    for g in gws:
        rows = load_stats(latest_stats(g))
        t0 = rows[0][0]
        t = [r[0] - t0 for r in rows]
        a1.plot(t, [r[1] for r in rows], color=COLOR[g], lw=2, label=LABEL[g])
        a2.plot(t, [r[2] for r in rows], color=COLOR[g], lw=2, label=LABEL[g])
    a1.axhline(100, color=INK2, lw=1, ls="--")
    a1.annotate("limite 1 vCPU", (1, 100), xycoords=("axes fraction", "data"), xytext=(-2, 3),
                textcoords="offset points", ha="right", fontsize=8, color=INK2)
    a2.axhline(512, color=INK2, lw=1, ls="--")
    a2.annotate("limite 512 Mo", (1, 512), xycoords=("axes fraction", "data"), xytext=(-2, -11),
                textcoords="offset points", ha="right", fontsize=8, color=INK2)
    a1.set(title="CPU pendant la montée en charge", xlabel="Temps (s)", ylabel="CPU (%)", ylim=(0, 125))
    a2.set(title="Mémoire pendant la montée en charge", xlabel="Temps (s)", ylabel="RAM (Mo)", ylim=(0, 560))
    a2.legend(loc="center right")
    fig.text(0.01, -0.03, "docker stats échantillonné en continu (≈ toutes les 2-3 s) pendant throughput.js. Source : results/<gw>-stats-*.csv (le plus récent)",
             fontsize=8, color=INK2)
    fig.tight_layout()
    save(fig, "04-cpu-ram.png", "CPU et RAM pendant la montée en charge")


# ---------------------------------------------------------------- 5. Rate limiting
def ratelimit_counts(path):
    res, metric = defaultdict(dict), None
    for line in read(path).splitlines():
        m = re.match(r"\s*(accepted|limited_429)\.", line)
        if m:
            metric = m.group(1)
            continue
        if re.match(r"\s*[a-z_]+\.{3,}", line):
            metric = None
        cm = re.search(r"\{ client:client-(\w+) \}\.+:\s*(\d+)", line)
        if cm and metric:
            res[cm.group(1)][metric] = int(cm.group(2))
    return res


def chart_ratelimit():
    gws = present(GATEWAYS, "{g}-ratelimit.log")
    if not gws:
        return
    clients = [("greedy", "gourmand\n(30 req/s)"), ("polite", "raisonnable\n(5 req/s)"), ("burst", "rafales\n(25 d'un coup)")]
    fig, axes = plt.subplots(1, len(gws), figsize=(4.6 * len(gws), 3.8), sharey=True, squeeze=False)
    for ax, g in zip(axes[0], gws):
        c = ratelimit_counts(os.path.join(RES, f"{g}-ratelimit.log"))
        xs = range(len(clients))
        acc = [c[k].get("accepted", 0) / 30 for k, _ in clients]
        lim = [c[k].get("limited_429", 0) / 30 for k, _ in clients]
        ax.bar(xs, acc, 0.6, color=COLOR[g], label="acceptées")
        ax.bar(xs, lim, 0.6, bottom=acc, color=STATUS["503"][0], hatch="//", edgecolor=SURFACE, label="refusées (429)")
        for x, a in zip(xs, acc):
            ax.annotate(f"{a:.2f}".replace(".", ","), (x, a), ha="center", va="bottom", fontsize=8, color=INK,
                        xytext=(0, 2), textcoords="offset points")
        ax.axhline(10, color=INK2, lw=1, ls="--")
        ax.annotate("quota 10 req/s", (len(clients) - 0.5, 10), xytext=(0, 3), textcoords="offset points",
                    ha="right", fontsize=8, color=INK2)
        ax.set_xticks(list(xs), [l for _, l in clients])
        ax.set_title(LABEL[g])
        ax.grid(axis="x", visible=False)
    axes[0][0].set_ylabel("Requêtes par seconde (moyenne sur 30 s)")
    axes[0][0].legend(loc="upper right")
    fig.suptitle("Rate limiting : 10 req/s par X-Client-Id", fontweight="bold")
    fig.text(0.01, -0.03, "Nombre affiché = débit accepté. Source : results/*-ratelimit.log", fontsize=8, color=INK2)
    fig.tight_layout()
    save(fig, "05-rate-limiting.png", "Rate limiting par client")


# ---------------------------------------------------------------- 6/7. Résilience (chronologies)
def timeline(path, step=5, key=1):
    rows = []
    for line in read(path).splitlines():
        m = re.search(r"CSV;(\d+);(\d+);([\d.]+);([\w-]+)", line)
        if m:
            rows.append((int(m.group(1)), m.group(2), m.group(4)))
    if not rows:
        return None, None
    rows.sort()
    t0 = rows[0][0]
    buckets = defaultdict(lambda: defaultdict(int))
    for t, st, inst in rows:
        buckets[int((t - t0) / 1000 // step) * step][st if key == 1 else inst] += 1
    return dict(buckets), t0


def chaos_window(t0, label_start, label_end, run_date="2026-11-02"):
    """Repère la fenêtre de panne (chaos-events.log, heure locale) relative au début du run."""
    p = os.path.join(RES, "chaos-events.log")
    if not os.path.exists(p) or t0 is None:
        return None
    import datetime
    import zoneinfo
    tz = zoneinfo.ZoneInfo("Europe/Paris")
    start = end = None
    for line in read(p).splitlines():
        hh, _, ev = line.partition(" ")
        try:
            ts = datetime.datetime.strptime(f"{run_date} {hh[:8]}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz).timestamp() * 1000
        except ValueError:
            continue
        rel = (ts - t0) / 1000
        if -15 <= rel <= 200:   # la panne peut démarrer pendant le setup() de k6, avant la 1re requête
            if label_start in ev:
                start = rel
            elif label_end in ev and start is not None:
                end = rel
    return (max(0.0, start), end) if start is not None else None


def chart_status_timeline(scenario, endpoint_title, ev_start, ev_end, fname, title):
    # Panneaux : (fichier, gateway pour la couleur, titre). Le run historique "passif seul" est montré en premier.
    panels = []
    hist = os.path.join(RES, f"kong-{scenario}-passif.log")
    if os.path.exists(hist):
        panels.append((hist, "kong", "Kong OSS 3.9 — health check passif seul (config initiale)"))
    for g in present(GATEWAYS, "{g}-" + scenario + ".log"):
        suffix = " — health checks actif + passif" if g == "kong" and panels else ""
        panels.append((os.path.join(RES, f"{g}-{scenario}.log"), g, LABEL[g] + suffix))
    if not panels:
        return
    fig, axes = plt.subplots(len(panels), 1, figsize=(9, 2.6 * len(panels)), sharex=True, squeeze=False)
    for ax, (path, g, ptitle) in zip(axes[:, 0], panels):
        b, t0 = timeline(path)
        if not b:
            continue
        xs = sorted(b)
        bottom = [0] * len(xs)
        for st in ["200", "500", "502", "504", "503"]:
            vals = [b[x].get(st, 0) for x in xs]
            if any(vals):
                col, lab = STATUS[st]
                ax.bar(xs, vals, 4.6, bottom=bottom, color=col, label=lab, align="edge",
                       hatch=None if st == "200" else ("//" if st == "503" else ".."), edgecolor=SURFACE)
                bottom = [a + v for a, v in zip(bottom, vals)]
        w = chaos_window(t0, ev_start, ev_end)
        if w:
            ax.axvspan(w[0], w[1] if w[1] else w[0] + 30, color=INK2, alpha=0.10, lw=0, zorder=0)
            ax.annotate("panne injectée", (w[0], ax.get_ylim()[1]), xytext=(3, 3), annotation_clip=False, textcoords="offset points",
                        fontsize=8, color=INK2)
        ax.set_title(ptitle, loc="left", fontsize=11, pad=16)
        ax.set_ylabel("Réponses / 5 s")
        ax.grid(axis="x", visible=False)
    axes[0, 0].legend(loc="lower right", bbox_to_anchor=(1, 1.02), ncol=3, fontsize=8)
    axes[-1, 0].set_xlabel("Temps depuis le début du test (s)")
    fig.suptitle(title, fontweight="bold", y=1.04)
    fig.text(0.01, -0.02, f"20 req/s sur {endpoint_title} pendant 120 s. Zone grisée = fenêtre de panne (chaos-events.log). "
             f"Source : results/*-{scenario}.log", fontsize=8, color=INK2)
    fig.tight_layout()
    save(fig, fname, title)


def chart_failover():
    gws = present(GATEWAYS, "{g}-kill-catalog2.log")
    if not gws:
        return
    fig, axes = plt.subplots(len(gws), 1, figsize=(9, 2.5 * len(gws)), sharex=True, squeeze=False)
    inst_color = {"catalog-1": "#2a78d6", "catalog-2": "#1baf7a", "none": STATUS["503"][0]}
    for ax, g in zip(axes[:, 0], gws):
        b, t0 = timeline(os.path.join(RES, f"{g}-kill-catalog2.log"), key=2)
        xs = sorted(b)
        bottom = [0] * len(xs)
        for inst in ["catalog-1", "catalog-2", "none"]:
            vals = [b[x].get(inst, 0) for x in xs]
            if any(vals):
                ax.bar(xs, vals, 4.6, bottom=bottom, color=inst_color[inst], align="edge", edgecolor=SURFACE,
                       label={"none": "erreur (aucune instance)"}.get(inst, f"servi par {inst}"))
                bottom = [a + v for a, v in zip(bottom, vals)]
        w = chaos_window(t0, "STOP catalog-2", "START catalog-2")
        if w:
            ax.axvspan(w[0], w[1] if w[1] else w[0] + 31, color=INK2, alpha=0.10, lw=0, zorder=0)
            ax.annotate("catalog-2 arrêté", (w[0], ax.get_ylim()[1]), xytext=(3, 3), annotation_clip=False, textcoords="offset points",
                        fontsize=8, color=INK2)
        ax.set_title(LABEL[g], loc="left", fontsize=11, pad=16)
        ax.set_ylabel("Réponses / 5 s")
        ax.grid(axis="x", visible=False)
    axes[0, 0].legend(loc="lower right", bbox_to_anchor=(1, 1.02), ncol=3, fontsize=8)
    axes[-1, 0].set_xlabel("Temps depuis le début du test (s)")
    fig.suptitle("Perte d'une instance du catalogue : qui répond ?", fontweight="bold", y=1.04)
    fig.text(0.01, -0.02, "20 req/s sur /api/catalog pendant 120 s. Source : results/*-kill-catalog2.log", fontsize=8, color=INK2)
    fig.tight_layout()
    save(fig, "07-failover-catalogue.png", "Failover lors de la perte d'une instance")


if __name__ == "__main__":
    print("Génération des graphiques dans docs/graphs/")
    chart_latency()
    chart_jwt()
    chart_throughput()
    chart_resources()
    chart_ratelimit()
    chart_status_timeline("errors-orders", "/api/orders", "orders error=0.5", "orders error=0",
                          "06-circuit-breaker.png", "Backend en erreur (50 % de 500) : ce que voit le client")
    chart_failover()
    # Index Markdown
    with open(os.path.join(ROOT, "docs", "graphs", "README.md"), "w", encoding="utf-8") as f:
        f.write("# Graphiques\n\nGénérés par `python3 scripts/graphs.py` à partir des fichiers de `results/`.\n\n")
        for name, title in generated:
            f.write(f"## {title}\n\n![{title}]({name})\n\n")
    print(f"{len(generated)} graphique(s).")
