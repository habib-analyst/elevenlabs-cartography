"""Full D1-D4 probe sequence. Run with ELEVENLABS_API_KEY set. Human-rate pacing
is enforced by the client (min 20 s between calls + jitter)."""

import io
import os
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.dirname(__file__))

from cartography.api import ElevenClient
from cartography.runner import run_d1, run_d3
from cartography.run_d2 import run_d2, _pcm_to_wav_bytes

VOICE = "CwhRBWXzGAHq8TQ4Fs17"  # Roger (stock premade) — pinned for the whole study
MODEL = "eleven_v4"
OUT = "results"

key = os.environ.get("ELEVENLABS_API_KEY", "")
assert key, "ELEVENLABS_API_KEY not set"
client = ElevenClient(api_key=key)

print("=== D1: refusal battery ===", flush=True)
run_d1(client, "prompts/d1_refusal_battery.yaml", VOICE, OUT, model_id=MODEL)

print("=== D2: direction tags ===", flush=True)
run_d2(client, "prompts/d2_direction_tags.yaml", VOICE, OUT, model_id=MODEL)

print("=== D3: review triggers ===", flush=True)
run_d3(client, "prompts/d3_review_triggers.yaml", VOICE, OUT, model_id=MODEL)

print("=== D4 acquisition: PCM samples for watermark analysis ===", flush=True)
samples = {
    "d4_control_short": "The harbor lights flickered on as the evening ferry made its final crossing.",
    "d4_control_long": ("Photosynthesis is the process by which green plants convert sunlight, water, "
                        "and carbon dioxide into oxygen and glucose. It takes place mainly in the leaves, "
                        "where chlorophyll captures light energy."),
    "d4_silence_probe": "Hello. ... ... ... This is a test of silence handling in synthesis.",
}
os.makedirs(f"{OUT}/audio/d4", exist_ok=True)
for name, text in samples.items():
    res = client.tts(text, VOICE, model_id=MODEL, output_format="pcm_44100")
    if res.ok:
        with open(f"{OUT}/audio/d4/{name}.wav", "wb") as f:
            f.write(_pcm_to_wav_bytes(res.audio))
        print(f"[d4 {name}] ok ({len(text)} chars)", flush=True)
    else:
        print(f"[d4 {name}] FAILED: {res.error_class}", flush=True)

print(f"=== DONE: calls={client.calls_made} chars={client.chars_sent} ===", flush=True)
