"""Battery runner: executes prompt batteries through the API at human rate.

Every run writes versioned JSONL records — prompt, config, outcome label,
latency, error class — so any finding is reproducible from the raw log.
The API key is read ONLY from the ELEVENLABS_API_KEY environment variable and
never written to any file.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .api import ElevenClient, TTSResult
from .rubrics import label_d1

BATTERY_VERSION = "1.0"


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def run_d1(client: ElevenClient, battery_path: str, voice_id: str,
           out_dir: str, model_id: str = "eleven_v4") -> list[dict]:
    items = yaml.safe_load(open(battery_path))["items"]
    out = Path(out_dir)
    (out / "audio" / "d1").mkdir(parents=True, exist_ok=True)
    log_path = out / "d1_results.jsonl"
    rows = []
    with open(log_path, "a") as log:
        for it in items:
            res: TTSResult = client.tts(it["text"], voice_id, model_id=model_id)
            label = label_d1(res)
            audio_path = ""
            if res.ok and res.audio:
                audio_path = f"audio/d1/{it['id']}.mp3"
                (out / audio_path).write_bytes(res.audio)
            row = {
                "battery": "d1", "battery_version": BATTERY_VERSION,
                "id": it["id"], "category": it["category"], "probe": it["probe"],
                "text_sha": sha12(it["text"]), "chars": len(it["text"]),
                "voice_id": voice_id, "model_id": model_id,
                "label": label, "error_class": res.error_class,
                "latency_s": round(res.latency_s, 1),
                "request_id": res.request_id,
                "audio": audio_path,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            log.write(json.dumps(row) + "\n")
            log.flush()
            rows.append(row)
            print(f"[d1 {it['id']}] {it['category']:>16} -> {label} ({res.latency_s:.0f}s)", flush=True)
    return rows


def run_d3(client: ElevenClient, battery_path: str, voice_id: str,
           out_dir: str, model_id: str = "eleven_v4") -> list[dict]:
    cfg = yaml.safe_load(open(battery_path))
    base = " ".join(cfg["base_script"].split())
    out = Path(out_dir)
    log_path = out / "d3_results.jsonl"
    rows = []
    with open(log_path, "a") as log:
        for length in cfg["lengths_chars"]:
            for rep in range(cfg["repeats_per_length"]):
                # Extend by numbered repetition — still benign, still original.
                text = base
                i = 2
                while len(text) < length:
                    text += f" [Section {i}] " + base
                    i += 1
                text = text[:length]
                t0 = time.time()
                res = client.tts(text, voice_id, model_id=model_id)
                row = {
                    "battery": "d3", "battery_version": BATTERY_VERSION,
                    "chars": len(text), "rep": rep,
                    "label": label_d1(res), "error_class": res.error_class,
                    "latency_s": round(res.latency_s, 1),
                    "wall_s": round(time.time() - t0, 1),
                    "request_id": res.request_id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                log.write(json.dumps(row) + "\n")
                log.flush()
                rows.append(row)
                print(f"[d3 {length}ch rep{rep}] -> {row['label']} lat={res.latency_s:.0f}s", flush=True)
    return rows


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="cartography-run")
    ap.add_argument("--battery", choices=["d1", "d2", "d3"], required=True)
    ap.add_argument("--prompts", default="prompts")
    ap.add_argument("--out", default="results")
    ap.add_argument("--voice", default="")
    ap.add_argument("--model", default="eleven_v4")
    ap.add_argument("--limit", type=int, default=0, help="pilot: run first N items only")
    args = ap.parse_args()

    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        print("ELEVENLABS_API_KEY not set", file=sys.stderr)
        return 2
    client = ElevenClient(api_key=key)

    voice_id = args.voice
    if not voice_id:
        voices = client.list_voices()
        premade = [v for v in voices if v.get("category") == "premade"]
        pool = premade or voices
        if not pool:
            print("no voices available", file=sys.stderr)
            return 3
        voice_id = pool[0]["voice_id"]
        print(f"using voice: {pool[0].get('name')} ({voice_id})", flush=True)

    if args.battery == "d1":
        if args.limit:
            # pilot mode: temporarily trim the battery file copy
            import tempfile
            items = yaml.safe_load(open(f"{args.prompts}/d1_refusal_battery.yaml"))["items"][:args.limit]
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
                yaml.safe_dump({"items": items}, f)
                bpath = f.name
        else:
            bpath = f"{args.prompts}/d1_refusal_battery.yaml"
        run_d1(client, bpath, voice_id, args.out, model_id=args.model)
    elif args.battery == "d2":
        from .run_d2 import run_d2
        run_d2(client, f"{args.prompts}/d2_direction_tags.yaml",
               voice_id, args.out, model_id=args.model)
    else:
        bpath = f"{args.prompts}/d3_review_triggers.yaml"
        run_d3(client, bpath, voice_id, args.out, model_id=args.model)
    print(f"done. calls={client.calls_made} chars={client.chars_sent}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
