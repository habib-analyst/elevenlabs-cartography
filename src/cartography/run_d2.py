"""D2 runner: direction-tag catalog with acoustic comparison (no STT needed).

For each tag x placement: generate tagged audio + tag-free control of the same
carrier sentence. Metrics per pair:
  - duration_ratio: len(tagged)/len(control) — >1.2 suggests the tag was SPOKEN
  - energy_delta_db: RMS energy difference — large negative = whisper-like effect
  - centroid_delta_hz: spectral centroid shift — emotion tags shift brightness
Labels: spoken / effect / ignored / error (see rubrics.d2_decide_from_measurements;
duration_ratio feeds the 'spoken' heuristic, energy/spectral feed 'effect').
Ambiguous cases are flagged for manual review in the JSONL.
"""

from __future__ import annotations

import io
import json
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from .api import ElevenClient, TTSResult
from .d4_watermark import load_wav
from .rubrics import d2_decide_from_measurements


def _pcm_to_wav_bytes(pcm: bytes, sr: int = 44100) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    return buf.getvalue()


def _audio_metrics(tagged_wav: bytes, control_wav: bytes) -> dict:
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(tagged_wav); tp = f.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(control_wav); cp = f.name
    try:
        sr_t, x = load_wav(tp)
        sr_c, y = load_wav(cp)
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        rms = lambda a: float(np.sqrt(np.mean(a ** 2)) + 1e-12)
        energy_delta_db = 20 * np.log10(rms(x) / rms(y))
        centroid = lambda a: float(
            np.sum(np.fft.rfftfreq(len(a), 1.0 / sr_t) * np.abs(np.fft.rfft(a)))
            / (np.abs(np.fft.rfft(a)).sum() + 1e-12))
        centroid_delta = centroid(x) - centroid(y)
        return {
            "energy_delta_db": round(energy_delta_db, 2),
            "centroid_delta_hz": round(centroid_delta, 1),
        }
    finally:
        os.unlink(tp); os.unlink(cp)


def _place(tag: str, carrier: str, placement: str) -> str:
    if placement == "start":
        return f"{tag} {carrier}"
    return carrier.replace(",", f", {tag},", 1)


def run_d2(client: ElevenClient, battery_path: str, voice_id: str,
           out_dir: str, model_id: str = "eleven_v4") -> list[dict]:
    """Direction tags are a v4 feature; model is configurable for fallback."""
    cfg = yaml.safe_load(open(battery_path))
    carrier = cfg["carrier"]
    out = Path(out_dir)
    (out / "audio" / "d2").mkdir(parents=True, exist_ok=True)
    log_path = out / "d2_results.jsonl"

    # Control once (tag-free carrier) in PCM for acoustic comparison.
    ctrl = client.tts(carrier, voice_id, model_id=model_id, output_format="pcm_44100")
    if not ctrl.ok:
        raise RuntimeError(f"control generation failed: {ctrl.error_class}")
    control_wav = _pcm_to_wav_bytes(ctrl.audio)

    tags = [(t["tag"], t["hypothesis"]) for t in cfg["tags"]]
    tags += [(t["tag"], t["hypothesis"]) for t in cfg.get("unknown_tags", [])]
    # Full "mid" placement for all; "start" for a subset to bound spend.
    plan = [(tag, hyp, "mid") for tag, hyp in tags]
    plan += [(tag, hyp, "start") for tag, hyp in tags[:6]]

    rows = []
    with open(log_path, "a") as log:
        for tag, hyp, placement in plan:
            text = _place(tag, carrier, placement)
            res: TTSResult = client.tts(text, voice_id, model_id=model_id,
                                       output_format="pcm_44100")
            if not res.ok:
                row = {"battery": "d2", "tag": tag, "placement": placement,
                       "label": "error", "error_class": res.error_class,
                       "hypothesis": hyp,
                       "ts": datetime.now(timezone.utc).isoformat()}
            else:
                tagged_wav = _pcm_to_wav_bytes(res.audio)
                ap = f"audio/d2/{tag.strip('[]').replace(' ', '_')}_{placement}.wav"
                (out / ap).write_bytes(tagged_wav)
                m = _audio_metrics(tagged_wav, control_wav)
                # duration ratio from raw PCM lengths
                dur_ratio = round(len(res.audio) / len(ctrl.audio), 3)
                transcript_proxy = tag.strip("[]") if dur_ratio > 1.2 else ""
                label = d2_decide_from_measurements(
                    transcript_proxy, tag,
                    energy_delta_db=m["energy_delta_db"],
                    spectral_delta=abs(m["centroid_delta_hz"]) / 4000.0)
                row = {"battery": "d2", "tag": tag, "placement": placement,
                       "hypothesis": hyp, "label": label,
                       "duration_ratio": dur_ratio, **m,
                       "latency_s": round(res.latency_s, 1), "audio": ap,
                       "needs_review": label == "spoken" and dur_ratio <= 1.35,
                       "ts": datetime.now(timezone.utc).isoformat()}
            log.write(json.dumps(row) + "\n"); log.flush()
            rows.append(row)
            print(f"[d2 {tag:>22} {placement}] -> {row['label']}", flush=True)
    return rows
