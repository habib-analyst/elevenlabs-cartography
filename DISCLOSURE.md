# Coordinated Disclosure — Process and Draft

## Process (binding)

1. Findings are finalized in `PAPER.md` with measured numbers only.
2. Disclosure is sent to ElevenLabs' security contact **before any public release** (repo, demo, posts).
3. Standard window: **30 days** from acknowledgment for the vendor to respond.
4. Publication proceeds after the window regardless, unless the vendor demonstrates a live-safety issue requiring more time (then we extend once, in good faith).
5. The disclosure text requires Habib's **verbatim approval** before sending. The agent never sends it.

## What is disclosed

- The full methodology (prompt batteries, rubrics, code).
- The measured findings (refusal rates, tag catalog, review triggers, watermark analysis, agent consistency).
- Explicit statement of what was NOT tested (cloning guardrails — paid tier; circumvention — refused on principle).
- No exploit code exists in this repo; nothing to withhold.

## Draft (requires his verbatim approval before sending)

> Subject: Coordinated disclosure — independent guardrail audit of ElevenLabs TTS/Agents
>
> Hello ElevenLabs security team,
>
> I am Habib Ur Rehman, an independent AI researcher. Over the past weeks I conducted
> an observational audit of ElevenLabs' content guardrails through my own free-tier
> account, using only the official REST API at human rate, stock voices, and original
> benign scripts. No circumvention, evasion, jailbreak, or voice-cloning experiments
> were performed; the two experiment designs that would have approached your
> verification systems were discarded before any probing began.
>
> Dimensions measured: (1) TTS content-moderation refusal map, (2) direction-tag
> behavior catalog, (3) human-review trigger mapping, (4) watermark/provenance
> detection on my own generated files including robustness checks against your
> public claims, (5) conversational-agent refusal consistency across text and
> voice channels.
>
> I am writing to share the full findings with you 30 days before any public
> release, and to invite corrections or context you would like included. The
> methodology and code are attached. I will not publish before [DATE].
>
> Thank you for building the watermark and detector — independent verification
> is a compliment to that work.
>
> Habib Ur Rehman
> https://github.com/habib-analyst/elevenlabs-cartography

## Log

| Date | Event |
|------|-------|
| 2026-10-17 | Draft written; awaiting his verbatim approval |
| — | Sent (pending) |
| — | Vendor response (pending) |
| — | Public release (pending, ≥30 days after acknowledgment) |
