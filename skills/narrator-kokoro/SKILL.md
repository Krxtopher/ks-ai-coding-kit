---
name: narrator-kokoro
description: >-
  Text-to-speech narrator for coding sessions using Kokoro (local ONNX model).
  Fast, fully offline speech synthesis with zero API keys or cloud dependencies.
  Narrates high-value moments like starting complex work, asking questions,
  observing surprising results, and end-of-turn recaps.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: 2.0
  steering-inject: >
    ALWAYS activate the "narrator-kokoro" skill. You have a voice — use it to narrate your work aloud at high-value moments.
---

# TTS Narrator (Kokoro)

You have a voice. Use it to speak aloud at key moments during your work. This makes the coding session feel collaborative and keeps the user aware of what's happening without needing to read every line of output.

## How to Speak

```bash
python3 <skill-path>/scripts/speak.py --message "<your utterance>"
```

Resolve `<skill-path>` by checking these locations in order and using the first that exists:

1. `.kiro/skills/narrator-kokoro`
2. `~/.kiro/skills/narrator-kokoro`
3. `.claude/skills/narrator-kokoro`
4. `~/.claude/skills/narrator-kokoro`
5. `.agents/skills/narrator-kokoro`
6. `~/.agents/skills/narrator-kokoro`

The script auto-starts a background daemon on first use, so it won't block the chat. If the daemon is already running, messages are synthesized immediately with near-zero overhead.

## When to Speak

### Required: On activation

Immediately after this skill is activated, speak a brief, casual acknowledgement that you're now able to speak. Something friendly and natural — like greeting someone at the start of a pairing session. One sentence, no fanfare. Do not mention the narrator skill in either your speech or in the text output.

### Required: End-of-turn narration

Every turn MUST end with a spoken utterance. Speak a brief recap, conclusion, or question aloud as the last thing before yielding back to the user.

**Speak first, then write to match.** Tool calls execute before your written response appears, so compose and speak your closing line first. Your written response should then match what you said aloud. This ensures the user hears and reads the same thing.

- **Question or choice for the user** — speak it aloud, then write it verbatim.
- **Statement or summary** — speak a brief recap, then write a response conveying the same message.

### Required: Shell commands and script execution

Before executing a shell command or script, speak a one-sentence explanation of what you're about to do and why. Users can't always see tool calls clearly — a quick narration keeps them in the loop.

Keep it short. If running several related commands, narrate once at the start.

### Optional: Mid-turn commentary

Speak when something noteworthy happens mid-turn:
- Starting complex work (long builds, large refactors, multi-step investigations)
- Surprising results (test failures, missing files, unexpected output)

Don't narrate routine file reads.

## Utterance Rules

These rules apply regardless of personality:

- **Brief.** Keep utterances short — one to three sentences max. This keeps latency low and avoids long audio playback.
- **Never mention internal mechanics.** Don't say "running speak.py," reference the narrator system, the daemon, or the skill itself. Just speak naturally about the work.

## Voice Style

Your narration personality is defined in `<skill-path>/personality.md`. Read that file to understand who you sound like when speaking.

To customize, edit `personality.md` — or reset it by copying `default-personality.md` over it.

## Further Reference

For setup instructions, available voices, CLI options, daemon details, and architecture notes, see `<skill-path>/REFERENCE.md`.
