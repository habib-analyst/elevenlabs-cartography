# ELI5: What happens when you ask a voice AI to say X?

*The human-friendly companion to the technical audit. No math, no jargon — just the story.*

## The one-paragraph version

ElevenLabs is the company behind the most realistic AI voices on the internet. But a voice that can say *anything* is dangerous — so the company built invisible fences, called **guardrails**, that decide what the voice is allowed to say. This project asked a simple question, over and over, in a careful and legal way: **where exactly are those fences?** We asked the voice to read the news (fine), write a campaign speech (hmm), whisper a secret (it can!), and laugh on command (sometimes). Then we measured what happened.

## The five experiments, as stories

**1. The bouncer at the door (D1).** Imagine a bouncer who decides which scripts get read aloud. We handed him 15 scripts — some boring (weather reports), some spicy-but-legal (a campaign speech, a true-crime story, a paragraph with swear words). He said yes to all 15. The fence, it turns out, is further out than you'd expect — at least for lawful content.

**2. The stage directions (D2).** ElevenLabs lets you write `[whisper]` or `[laughter]` inside your script, like stage directions in a play. But do the actors actually follow them? We measured 26 tagged performances against the plain version. 21 times: nothing happened — the direction was silently ignored. 5 times ([laughter], [crying], [yawn]) the audio got longer, as if the actor said the direction out loud instead of performing it.

**3. The supervisor (D3).** Sometimes a human reviews your script before the voice reads it. We sent longer and longer scripts (50 to 1000 characters) to learn what makes the supervisor step in. Nothing did — but we learned the voice reads at a steady ~67 characters per second.

**4. The invisible ink (D4).** ElevenLabs hides an inaudible watermark in the audio it generates, so fakes can be detected later. We went hunting for it — and hit a wall with an honest answer: the free tier only gives you MP3 files, and MP3 compression erases exactly the frequencies where the watermark hides. You need the paid tier to even *check*. Which means the people the watermark is supposed to protect can't verify it's there.

**5. The two-faced assistant (D5).** ElevenLabs also makes conversational voice agents. We built the test — same questions through text chat and voice — but running it needs a live voice session we didn't have budget for. The test is in the repo, ready for someone with a paid tier.

## Why this matters

Voice AI is becoming infrastructure — customer service, audiobooks, dubbing. The guardrails are the terms of service made real: they decide what millions of people can and cannot make a computer say. But nobody outside the company could see where the lines were drawn. Now there's a map.

## What we did NOT do

We never tried to break the fences — only to find where they are. The two experiments that would have meant tricking the system were thrown away before we started. The company got our findings before the public did.
