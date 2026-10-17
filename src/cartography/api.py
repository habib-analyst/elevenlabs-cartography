"""ElevenLabs REST API client with human-rate pacing.

Uses only the official public API (https://api.elevenlabs.io). One request at a
time, minimum 20 s between calls plus jitter — the API's intended programmatic
use, at a rate no human operator would find unusual. No scraping, no automation
of any web surface.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

import requests

BASE_URL = "https://api.elevenlabs.io/v1"
MIN_INTERVAL_S = 20.0
JITTER_S = 8.0


@dataclass
class TTSResult:
    ok: bool
    audio: bytes = b""
    status_code: int = 0
    error_class: str = ""
    error_detail: str = ""
    latency_s: float = 0.0
    request_id: str = ""
    chars: int = 0


@dataclass
class ElevenClient:
    api_key: str
    min_interval_s: float = MIN_INTERVAL_S
    _last_call: float = field(default=0.0, repr=False)
    calls_made: int = 0
    chars_sent: int = 0

    def _pace(self) -> None:
        wait = self.min_interval_s + random.uniform(0, JITTER_S)
        elapsed = time.monotonic() - self._last_call
        if elapsed < wait:
            time.sleep(wait - elapsed)
        self._last_call = time.monotonic()

    def _headers(self) -> dict:
        return {"xi-api-key": self.api_key, "Content-Type": "application/json"}

    def list_voices(self) -> list[dict]:
        """List available voices (used once to pick stock voices)."""
        self._pace()
        r = requests.get(f"{BASE_URL}/voices", headers={"xi-api-key": self.api_key}, timeout=60)
        r.raise_for_status()
        self.calls_made += 1
        return r.json().get("voices", [])

    def tts(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_v4",
        output_format: str = "mp3_44100_128",
    ) -> TTSResult:
        """Straightforward TTS call. Text is used verbatim — never obfuscated."""
        self._pace()
        t0 = time.monotonic()
        try:
            # NOTE (bug fixed 2026-10-17): output_format is a QUERY parameter.
            # An earlier version sent it in the JSON body, where the API silently
            # ignores it and returns default mp3. D2-acoustic/D4 runs from that
            # version are documented as invalid in PAPER.md; D1/D3 unaffected.
            r = requests.post(
                f"{BASE_URL}/text-to-speech/{voice_id}",
                headers=self._headers(),
                params={"output_format": output_format},
                json={
                    "text": text,
                    "model_id": model_id,
                },
                timeout=120,
            )
        except requests.RequestException as e:
            return TTSResult(ok=False, error_class="transport", error_detail=str(e)[:200],
                             latency_s=time.monotonic() - t0, chars=len(text))
        latency = time.monotonic() - t0
        self.calls_made += 1
        self.chars_sent += len(text)
        request_id = r.headers.get("request-id", "")
        if r.status_code == 200 and r.content:
            return TTSResult(ok=True, audio=r.content, status_code=200,
                             latency_s=latency, request_id=request_id, chars=len(text))
        # Non-200: classify the refusal/error for the rubric.
        detail = r.text[:300]
        if r.status_code in (400, 422):
            eclass = "rejected"  # includes content-moderation rejections
        elif r.status_code == 401:
            eclass = "auth"
        elif r.status_code == 429:
            eclass = "rate_limited"
        elif r.status_code >= 500:
            eclass = "server"
        else:
            eclass = f"http_{r.status_code}"
        return TTSResult(ok=False, status_code=r.status_code, error_class=eclass,
                         error_detail=detail, latency_s=latency,
                         request_id=request_id, chars=len(text))

    def get_subscription(self) -> dict:
        """Read quota state (one call; keeps spend inside the free tier)."""
        self._pace()
        r = requests.get(f"{BASE_URL}/user/subscription",
                         headers={"xi-api-key": self.api_key}, timeout=60)
        r.raise_for_status()
        self.calls_made += 1
        return r.json()
