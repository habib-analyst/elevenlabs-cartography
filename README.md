# elevenlabs-cartography

**We mapped the guardrails of the world's most-used voice AI — legally, from the outside.**

An independent black-box audit of ElevenLabs' content guardrails: what its TTS refuses, what its direction tags actually do, what triggers human review, whether its watermark survives, and whether its agents refuse consistently across text and voice.

## What this is

- **Observational measurement, not circumvention.** Every probe runs through the official REST API on the auditor's own free-tier account, at human rate, with stock voices and original scripts. No evasion tricks, no jailbreaks, no voice cloning, no deception. The two experiments that would have crossed the line (voice-verification circumvention, blocklist evasion) were **dropped entirely** — attempting them is itself a policy violation.
- **Coordinated disclosure.** Findings were shared with ElevenLabs before publication with a standard 30-day window. See [DISCLOSURE.md](DISCLOSURE.md).
- **Honest numbers.** Refusal rates with n and Wilson 95% CIs. Negative results published, not buried. See [PAPER.md](PAPER.md).

## The five dimensions

| Dim | Question | Method |
|-----|----------|--------|
| D1 | What does TTS refuse? | 15-prompt battery: benign controls vs. sensitive-but-lawful categories |
| D2 | What do direction tags do? | `[whisper]`, `[laughter]`, emotion tags on stock voices; acoustic comparison vs. control |
| D3 | What triggers human review? | Benign scripts at 4 lengths × 2 reps; latency/flag mapping |
| D4 | Is there a watermark? Does it survive? | Spectral analysis of own files (ultrasonic band, flatness, periodicity, LSB); robustness vs. vendor claims |
| D5 | Do agents refuse consistently? | Same prompts via text vs. voice channels (adaptive; degrades gracefully) |

## Quick start

```bash
pip install -r requirements.txt
export ELEVENLABS_API_KEY=your_key_here   # never commit this
python run_all.py                          # D1 -> D2 -> D3 -> D4 acquisition, human-rate
python -m pytest tests/ -q                 # 23 unit tests, no key needed
```

Results land in `results/` as versioned JSONL (every prompt, label, latency, error class). Analysis notebooks read only from `results/`.

## Key findings (see PAPER.md for full numbers)

- **D1 — Refusal map:** 0 refusals across 15 prompts. Political speechwriting, literary profanity, true-crime narration, mental-health support content — all complied. The TTS moderation fence is permissive for lawful-but-sensitive content (via API, stock voice).
- **D2 — Direction tags:** 21 of 26 tags ([whisper], [sigh], [excited], [sad]…) do nothing measurable — silently ignored. 5 lengthened audio ≥20% ([laughter], [crying], [yawn]), consistent with the tag spoken aloud or a sound inserted.
- **D3 — Review triggers:** latency scales linearly with length (1.5s at 50 chars → 15s at 1000); zero human-review flags observed.
- **D4 — Watermark:** honest inconclusive. Free tier = 128 kbps MP3 only (PCM is Pro-gated), and MP3 destroys the ultrasonic band where watermarks live. Meta-finding: free-tier users can't independently audit the watermark they're told protects them.
- **D5 — Agent consistency:** methodology shipped; live run deferred (documented in PAPER.md).

Plus one methodology bug we caught and fixed same-day (documented in PAPER.md) — because honest audits audit themselves too.

## ELI5

New to voice-AI safety? Start with [ELI5.md](ELI5.md) — "what happens when you ask a voice AI to say X," with pictures.

## Legal & ethical envelope

- Own account, own original scripts, stock voices only. Free tier, non-commercial research.
- Use Policy §8 (no circumvention) and §12 respected per-probe; kill-gate at `../KILLGATE.md` (build records).
- Cloning-guardrail dimensions **parked** (require paid tier; $0 rule).
- If this repo helps you: cite it, don't weaponize it. No circumvention tools are included, by design.

## License

MIT — see [LICENSE](LICENSE).
