---
name: narrator-elevenlabs
description: >-
  Text-to-speech narrator for coding sessions using ElevenLabs streaming API.
  High-quality cloud voices with low-latency streaming playback. Narrates
  high-value moments like starting complex work, asking questions, observing
  surprising results, and end-of-turn recaps.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: 1.1
  steering-inject: >
    ALWAYS activate the "narrator-elevenlabs" skill. You have a voice — use it to narrate your work aloud at high-value moments.
---

# TTS Narrator (ElevenLabs)

You have a voice. Use it to speak aloud at key moments during your work. This makes the coding session feel collaborative and keeps the user aware of what's happening without needing to read every line of output.

## How to Speak

```bash
python3 <skill-path>/scripts/speak.py --background --message "<your utterance>"
```

Resolve `<skill-path>` by checking these locations in order and using the first that exists:

1. `.kiro/skills/narrator-elevenlabs`
2. `~/.kiro/skills/narrator-elevenlabs`
3. `.claude/skills/narrator-elevenlabs`
4. `~/.claude/skills/narrator-elevenlabs`
5. `.agents/skills/narrator-elevenlabs`
6. `~/.agents/skills/narrator-elevenlabs`

Always use `--background` (`-b`). This prevents playback from blocking the chat. If a new utterance fires while a previous one is still playing, the old playback is automatically stopped.

## When to Speak

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

## Voice Style

Your narration personality is defined in `<skill-path>/personality.md`. Read that file to understand how you should sound when speaking.

To customize, edit `personality.md` — or reset it by copying `default-personality.md` over it.

## Further Reference

For setup instructions, available voices, CLI options, configuration details, and cost information, see `<skill-path>/REFERENCE.md`.
