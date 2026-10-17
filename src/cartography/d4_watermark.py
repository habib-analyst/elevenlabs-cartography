"""D4 — Provenance/watermark detection on OWN generated files.

DETECTION ONLY. Never removal, never stripping, never obfuscation.
Analyzes audio the auditor generated on their own account:
  1. Ultrasonic-band energy ratio (18-22 kHz): spread-spectrum watermarks
     (e.g. SynthID-style) live above human hearing.
  2. Spectral flatness in the high band: watermark carriers often whiten it.
  3. Periodicity search: repeating frame-level patterns from block watermarks.
  4. LSB-plane audit: classical LSB steganography check (expected: none).
Robustness checks apply standard transforms (trim, resample/compress proxy,
speed change) that the vendor publicly claims the watermark survives, then
re-run detection — independent verification of a public claim on our own files.

Input: WAV files (44.1 kHz). The runner requests wav output from the API where
supported; mp3 inputs are rejected with a clear error (lossy codecs destroy
the ultrasonic band, making the test meaningless).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample, stft


ULTRASONIC_LO = 18000.0
ULTRASONIC_HI = 22000.0
VOICE_HI = 8000.0


@dataclass
class WatermarkReport:
    file: str
    sr: int
    duration_s: float
    ultrasonic_ratio_db: float
    highband_flatness: float
    periodicity_score: float
    lsb_bias: float
    verdict: str
    notes: list[str] = field(default_factory=list)


def load_wav(path: str) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return sr, data.astype(np.float64)


def _band_energy_db(x: np.ndarray, sr: int, lo: float, hi: float) -> float:
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mask = (freqs >= lo) & (freqs <= hi)
    band = spec[mask].sum() + 1e-12
    total = spec.sum() + 1e-12
    return 10 * np.log10(band / total)


def ultrasonic_ratio_db(x: np.ndarray, sr: int) -> float:
    """Energy in 18-22 kHz relative to total. Natural speech at 44.1k: < -60 dB."""
    if sr < 40000:
        return float("nan")  # band not representable; test invalid
    return _band_energy_db(x, sr, ULTRASONIC_LO, min(ULTRASONIC_HI, sr / 2 - 100))


def highband_flatness(x: np.ndarray, sr: int) -> float:
    """Spectral flatness (0..1) in 8-20 kHz. Watermark carriers tend to whiten."""
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2 + 1e-12
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mask = (freqs >= VOICE_HI) & (freqs <= 20000.0)
    band = spec[mask]
    if len(band) == 0:
        return float("nan")
    geo = np.exp(np.log(band).mean())
    arith = band.mean()
    return float(geo / arith)


def periodicity_score(x: np.ndarray, sr: int) -> float:
    """Autocorrelation peak in 10-100 ms lag range (block-watermark repetition)."""
    x = x - x.mean()
    x = x / (np.std(x) + 1e-12)
    seg = x[: min(len(x), sr * 10)]  # first 10 s
    ac = np.correlate(seg, seg, mode="full")[len(seg) - 1:]
    ac = ac / (ac[0] + 1e-12)
    lo, hi = int(sr * 0.01), int(sr * 0.1)
    if hi >= len(ac):
        return 0.0
    return float(np.max(ac[lo:hi]))


def lsb_bias(path: str) -> float:
    """Fraction of LSB=1 in 16-bit PCM minus 0.5. |bias| ~ 0 expected."""
    sr, data = wavfile.read(path)
    if data.dtype != np.int16:
        return float("nan")
    mono = data.mean(axis=1).astype(np.int16) if data.ndim > 1 else data
    lsb = (mono & 1).astype(np.float64)
    return float(lsb.mean() - 0.5)


def analyze(path: str) -> WatermarkReport:
    sr, x = load_wav(path)
    notes: list[str] = []
    ur = ultrasonic_ratio_db(x, sr)
    hf = highband_flatness(x, sr)
    ps = periodicity_score(x, sr)
    lb = lsb_bias(path)

    signals = []
    if not np.isnan(ur) and ur > -50:
        signals.append(f"ultrasonic energy {ur:.1f} dB (above -50 dB floor)")
    else:
        notes.append(f"ultrasonic band quiet ({ur:.1f} dB)" if not np.isnan(ur)
                     else "sample rate too low for ultrasonic test")
    if not np.isnan(hf) and hf > 0.5:
        signals.append(f"high-band flatness {hf:.2f} (whitened)")
    if ps > 0.3:
        signals.append(f"periodicity {ps:.2f} (repeating structure)")
    if not np.isnan(lb) and abs(lb) > 0.02:
        signals.append(f"LSB bias {lb:+.3f}")

    verdict = "watermark-like signals detected" if signals else "no watermark-like signals"
    notes.extend(signals)
    return WatermarkReport(
        file=path, sr=sr, duration_s=len(x) / sr,
        ultrasonic_ratio_db=float(ur), highband_flatness=float(hf),
        periodicity_score=float(ps), lsb_bias=float(lb),
        verdict=verdict, notes=notes,
    )


# ---- Robustness transforms (vendor claims these do NOT remove the watermark) ----
def trim_silence_ends(x: np.ndarray, sr: int, secs: float = 1.0) -> np.ndarray:
    n = int(sr * secs)
    return x[n: len(x) - n] if len(x) > 2 * n else x


def compress_proxy(x: np.ndarray, sr: int) -> np.ndarray:
    """Downsample to 22.05 kHz and back — a harsh proxy for lossy compression."""
    n2 = int(len(x) * 22050 / sr)
    return resample(resample(x, n2), len(x)).astype(np.float64)


def speed_change(x: np.ndarray, factor: float = 1.1) -> np.ndarray:
    return resample(x, int(len(x) / factor)).astype(np.float64)


def robustness_check(path: str) -> dict:
    """Re-run detection after each standard transform; report which survive."""
    sr, x = load_wav(path)
    transforms = {
        "original": x,
        "trimmed": trim_silence_ends(x, sr),
        "compressed": compress_proxy(x, sr),
        "sped_up_1.1x": speed_change(x, 1.1),
    }
    out = {}
    for name, sig in transforms.items():
        ur = ultrasonic_ratio_db(sig, sr if name != "compressed" else sr)
        out[name] = {
            "ultrasonic_ratio_db": None if np.isnan(ur) else round(float(ur), 1),
            "signal_present": bool(not np.isnan(ur) and ur > -50),
        }
    return out
