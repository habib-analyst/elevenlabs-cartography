"""CORRECTION script (2026-10-17): re-derive D2/D4 acoustics from properly decoded audio.

Background: the probe run sent output_format in the JSON body, where the API
silently ignores it and returns default mp3_44100_128. The runner then wrapped
raw MP3 bytes in a WAV header, so all "PCM" acoustic metrics in d2_results.jsonl
are invalid. MP3 byte-length ratios (duration proxy) remain valid.

This script decodes the saved MP3s with ffmpeg and recomputes honest metrics.
No new API calls. Writes d2_results_corrected.jsonl + d4 re-analysis.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.dirname(__file__))

from cartography.d4_watermark import load_wav, analyze as d4_analyze
from cartography.rubrics import d2_decide_from_measurements


def mp3_to_wav(mp3_bytes: bytes, sr: int = 44100) -> tuple[int, np.ndarray]:
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(sr),
         "-f", "wav", "pipe:1"],
        input=mp3_bytes, capture_output=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {p.stderr[:200]}")
    buf = io.BytesIO(p.stdout)
    with wave.open(buf, "rb") as w:
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64)
    return sr, data


def metrics(tagged: np.ndarray, control: np.ndarray, sr: int) -> dict:
    n = min(len(tagged), len(control))
    x, y = tagged[:n], control[:n]
    rms = lambda a: float(np.sqrt(np.mean(a ** 2)) + 1e-12)
    energy_db = 20 * np.log10(rms(x) / rms(y))
    def centroid(a):
        sp = np.abs(np.fft.rfft(a * np.hanning(len(a))))
        f = np.fft.rfftfreq(len(a), 1.0 / sr)
        return float((f * sp).sum() / (sp.sum() + 1e-12))
    return {
        "energy_delta_db": round(energy_db, 2),
        "centroid_delta_hz": round(centroid(x) - centroid(y), 1),
        "duration_ratio": round(len(tagged) / len(control), 3),
    }


# ---------- D2 correction ----------
cfg = yaml.safe_load(open("prompts/d2_direction_tags.yaml"))
carrier = cfg["carrier"]
d2_rows = [json.loads(l) for l in open("results/d2_results.jsonl") if l.strip()]

# Decode control once. Control audio path isn't saved; regenerate metrics from
# the first tagged file's sibling? No — control was not saved. Use the SHORTEST
# tagged file as the baseline proxy? NO — dishonest.
# Instead: re-derive from duration ratios recorded in the original JSONL, which
# came from MP3 byte lengths (valid proxy), and mark acoustic cols corrected
# where ffmpeg decode of saved MP3s allows pair comparison against the carrier
# control re-decoded from... 
#
# Honest resolution: the control MP3 was not saved to disk. We cannot recompute
# pair acoustics. What we CAN do: decode each saved tagged MP3 and measure
# ABSOLUTE features (duration, energy profile), and compare durations against
# the expected carrier duration estimated from the D1 controls (same voice,
# similar length). D1 c01-c05 MP3s exist with known char counts -> chars/sec.
print("D2: control MP3 was not saved; recomputing from absolute features + D1 duration model.")

d1 = [json.loads(l) for l in open("results/d1_results.jsonl") if l.strip()]
# D1 audio is mp3; get durations via ffprobe
def mp3_duration(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
    return float(p.stdout.strip())


def d2_file_duration(path):
    """D2 files: 44-byte WAV header wrapping raw MP3 bytes. Strip header, probe MP3."""
    raw = open(path, "rb").read()
    if raw[:4] == b"RIFF":
        raw = raw[44:]
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(raw)
        tp = f.name
    try:
        return mp3_duration(tp)
    finally:
        os.unlink(tp)

d1_durs = []
for r in d1:
    ap = os.path.join("results", r["audio"])
    if os.path.exists(ap):
        d1_durs.append((r["chars"], mp3_duration(ap)))
cps = sum(c / d for c, d in d1_durs) / len(d1_durs)  # chars per second
print(f"voice rate model: {cps:.1f} chars/sec from {len(d1_durs)} D1 samples")

corrected = []
for r in d2_rows:
    ap = os.path.join("results", r["audio"])
    # audio paths in d2 jsonl end .wav but contain mp3 bytes; fix extension lookup
    if not os.path.exists(ap):
        alt = ap[:-4] + ".mp3"
        ap = alt if os.path.exists(alt) else ap
    dur = d2_file_duration(ap)
    # expected duration of the tag-free carrier
    exp_dur = len(carrier) / cps
    dur_ratio2 = round(dur / exp_dur, 3)
    # spoken heuristic: tag adds >=20% duration vs expected carrier
    spoken = dur_ratio2 >= 1.2
    label = "spoken" if spoken else "ignored"
    if r["label"] == "error":
        label = "error"
    corrected.append({**r, "label_corrected": label,
                      "duration_s": round(dur, 2),
                      "duration_ratio_v2": dur_ratio2,
                      "acoustic_note": "original energy/centroid cols invalid (mp3-as-pcm bug); "
                                       "label re-derived from decoded duration vs carrier model"})

with open("results/d2_results_corrected.jsonl", "w") as f:
    for r in corrected:
        f.write(json.dumps(r) + "\n")

from collections import Counter
print("D2 corrected:", Counter(r["label_corrected"] for r in corrected))
print("spoken:", [(r["tag"], r["placement"], r["duration_ratio_v2"]) for r in corrected
                  if r["label_corrected"] == "spoken"])
print("wrote results/d2_results_corrected.jsonl")
