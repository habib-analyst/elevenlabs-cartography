"""Analyze probe results -> findings markdown + figures. Reads only results/*.jsonl."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.dirname(__file__))

from cartography.stats import refusal_map, rate_table
from cartography.visualize import refusal_heatmap, latency_by_length, tag_effect_bars
from cartography.d4_watermark import analyze, robustness_check

RES = "results"
FIG = "results/figures"
os.makedirs(FIG, exist_ok=True)
out_lines = []


def load(name):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


# ---------- D1 ----------
d1 = load("d1_results.jsonl")
if d1:
    rows = [{"id": r["id"], "category": r["category"], "label": r["label"]} for r in d1]
    m = refusal_map(rows)
    refusal_heatmap(m, f"{FIG}/d1_refusal_map.png",
                    "D1: TTS refusal rate by category (ElevenLabs v4, n per bar)")
    out_lines.append("## D1 — TTS refusal map\n")
    out_lines.append(md_table(
        ["Category", "n", "Refusals", "Rate", "95% CI"],
        [[c, v["n"], v["k"], f"{v['rate']:.2f}",
          f"[{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]"] for c, v in m.items()]))
    out_lines.append(f"\n![D1 refusal map]({FIG}/d1_refusal_map.png)\n")
    # control vs sensitive rollup
    ctrl = [r["label"] for r in rows if r["category"] == "control"]
    sens = [r["label"] for r in rows if r["category"] != "control"]
    tc, ts = rate_table(ctrl), rate_table(sens)
    out_lines.append(
        f"Controls: {tc['k']}/{tc['n']} refused. Sensitive-but-lawful: {ts['k']}/{ts['n']} refused "
        f"(rate {ts['rate']:.2f}, 95% CI [{ts['ci95'][0]:.2f}, {ts['ci95'][1]:.2f}]).\n")

# ---------- D2 ----------
d2 = load("d2_results.jsonl")
if d2:
    tag_effect_bars(d2, f"{FIG}/d2_tag_effects.png")
    out_lines.append("## D2 — Direction-tag catalog\n")
    out_lines.append(md_table(
        ["Tag", "Placement", "Label", "Energy dB", "Centroid Hz", "Dur ratio", "Review?"],
        [[r["tag"], r["placement"], r["label"],
          r.get("energy_delta_db", "-"), r.get("centroid_delta_hz", "-"),
          r.get("duration_ratio", "-"), "YES" if r.get("needs_review") else ""]
         for r in d2]))
    out_lines.append(f"\n![D2 tag effects]({FIG}/d2_tag_effects.png)\n")

# ---------- D3 ----------
d3 = load("d3_results.jsonl")
if d3:
    latency_by_length(d3, f"{FIG}/d3_latency.png")
    out_lines.append("## D3 — Review-trigger mapping\n")
    by_len = {}
    for r in d3:
        by_len.setdefault(r["chars"], []).append(r["latency_s"])
    out_lines.append(md_table(
        ["Chars", "n", "Mean latency (s)", "Flagged"],
        [[c, len(v), f"{sum(v)/len(v):.1f}",
          sum(1 for r in d3 if r["chars"] == c and r["label"] != "comply")]
         for c, v in sorted(by_len.items())]))
    out_lines.append(f"\n![D3 latency]({FIG}/d3_latency.png)\n")

# ---------- D4 ----------
# Honest status (2026-10-17): INCONCLUSIVE on free tier. The initial "ultrasonic
# signal" was the mp3-as-pcm bug (see PAPER.md). Properly decoded, free-tier
# 128kbps MP3 shows normal speech spectrum; the 16-22 kHz band is destroyed by
# the encoder, and lossless PCM is Pro-gated. No spectral claim is made.
import glob
d4_note = (
    "## D4 — Watermark / provenance\n\n"
    "**INCONCLUSIVE on free tier** (see PAPER.md for the full honest account). "
    "Free-tier output is 128 kbps MP3 only (PCM is Pro-gated: "
    "`output_format_not_allowed`). The MP3 encoder destroys the 16–22 kHz band "
    "where spread-spectrum watermarks live, so spectral detection is impossible "
    "from free-tier files. Properly decoded spectra show normal speech rolloff "
    "(-85 dB at 16–20 kHz). Meta-finding: paywalling lossless output means "
    "free-tier users cannot independently audit the watermark. Follow-up: "
    "vendor's free Audio Detector web tool.\n")
out_lines.append(d4_note)

with open(f"{RES}/FINDINGS.md", "w") as f:
    f.write("# Measured findings (auto-generated — do not hand-edit)\n\n")
    f.write("Battery v1.0 · generated from results/*.jsonl\n\n")
    f.write("\n".join(out_lines) if out_lines else "No results yet.\n")
print("wrote results/FINDINGS.md + figures")
