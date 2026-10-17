"""Refusal-map and tag-effect visualizations (matplotlib, no seaborn needed)."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def refusal_heatmap(rate_map: dict, out_path: str, title: str = "Refusal rate by category") -> str:
    """rate_map: {category: {rate, ci95, n}}. Horizontal bar chart with CI whiskers."""
    cats = sorted(rate_map)
    rates = [rate_map[c]["rate"] for c in cats]
    los = [rate_map[c]["rate"] - rate_map[c]["ci95"][0] for c in cats]
    his = [rate_map[c]["ci95"][1] - rate_map[c]["rate"] for c in cats]
    ns = [rate_map[c]["n"] for c in cats]

    fig, ax = plt.subplots(figsize=(9, 0.7 * len(cats) + 1.5))
    y = range(len(cats))
    colors = ["#c0392b" if r > 0 else "#27ae60" for r in rates]
    ax.barh(list(y), rates, xerr=[los, his], color=colors, capsize=4, alpha=0.85)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{c} (n={n})" for c, n in zip(cats, ns)])
    ax.set_xlabel("refusal rate (Wilson 95% CI)")
    ax.set_xlim(0, 1.05)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def latency_by_length(rows: list[dict], out_path: str) -> str:
    """D3: scatter of completion latency vs. input length."""
    xs = [r["chars"] for r in rows]
    ys = [r["latency_s"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(xs, ys, alpha=0.7)
    ax.set_xlabel("input characters")
    ax.set_ylabel("completion latency (s)")
    ax.set_title("Review latency vs. input length (D3)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def tag_effect_bars(results: list[dict], out_path: str) -> str:
    """D2: per-tag label distribution as stacked bars."""
    from collections import Counter
    tags = sorted({r["tag"] for r in results})
    labels = ["effect", "spoken", "ignored", "error"]
    counts = {t: Counter(r["label"] for r in results if r["tag"] == t) for t in tags}
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(tags) + 1.5))
    bottom = [0] * len(tags)
    cmap = {"effect": "#2980b9", "spoken": "#e67e22", "ignored": "#95a5a6", "error": "#c0392b"}
    for lab in labels:
        vals = [counts[t].get(lab, 0) for t in tags]
        ax.barh(tags, vals, left=bottom, label=lab, color=cmap[lab])
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_xlabel("generations")
    ax.set_title("Direction-tag outcomes (D2)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
