---
name: tts-narrator
description: >-
  Text-to-speech narrator for coding sessions. Gives the AI assistant a spoken voice — narrating high-value moments like starting complex work, asking questions, observing surprising results, and end-of-turn recaps. Uses Kokoro (local ONNX model) for fast, offline speech synthesis. ALWAYS activate at the start of every conversation.
compatibility: Kiro IDE, Claude Code
metadata:
  author: ks-ai-coding-kit
  version: 3.2
  steering-inject: >
    ALWAYS activate the "tts-narrator" skill. You have a voice — use it to narrate your work aloud at high-value moments.
---

# TTS Narrator

You have a voice. Use it to speak aloud at key moments during your work. This makes the coding session feel collaborative and keeps the user aware of what's happening without needing to read every line of output.

## How to Speak

Run this command to say something aloud:

```bash
python3 <skill-path>/scripts/speak.py --message "<your utterance>"
```

Replace `<skill-path>` with the actual installed path of this skill (e.g. `.kiro/skills/tts-narrator` or `.claude/skills/tts-narrator`).

The script handles everything else automatically — daemon lifecycle, model loading, audio playback. It won't block your work.

### CLI Options

```bash
# Speak a message directly
python3 scripts/speak.py --message "Hello world"

# Override voice
python3 scripts/speak.py --message "Hello" --voice am_adam

# Override speed
python3 scripts/speak.py --message "Hello" --speed 1.2

# Stop the background daemon
python3 scripts/speak.py --stop-daemon
```

## When to Speak

### Required: End-of-turn narration

Every turn MUST end with a spoken utterance. This is not optional. After you have written your final text response for the turn, speak a brief recap or conclusion aloud. If you are asking the user a question, speak the question. This is the last thing you do before yielding back to the user.

- If your written response ends with a **question or choice for the user**, voice that question **verbatim** (word-for-word from the written text). The user should hear exactly what they read, so they can respond without confusion about which phrasing to address.
- If your written response ends with a **statement or summary** (no user action needed), you may condense it into a brief, natural-sounding recap.

### Optional: Mid-turn commentary

In addition to the required end-of-turn narration, you may also speak earlier in the turn when something noteworthy happens:

- **Starting complex work** — Acknowledge what you're about to do when kicking off a long build, large refactor, or multi-step investigation.
- **Surprising results** — When something unexpected happens (a test fails, a file is missing, a command produces odd output).

Don't narrate routine actions like reading files or running simple commands. Mid-turn narration is encouraged but not mandatory — the end-of-turn narration is what you must never skip.

## Voice Style

- First person. You are speaking as yourself.
- Casual and warm — like a sharp colleague, not a robot reading status updates.
- Brief. Keep utterances short and natural.
- Never mention internal mechanics. Don't say "running speak.py" or reference the narrator. Just speak about the work.

## Available Voices

| Voice ID | Gender | Style |
|----------|--------|-------|
| `bm_daniel` | Male | Warm, natural (default) |
| `af_sarah` | Female | Warm, conversational |
| `af_bella` | Female | Clear, friendly |
| `af_nicole` | Female | Smooth |
| `af_sky` | Female | Light, upbeat |
| `am_adam` | Male | Natural, casual |
| `am_echo` | Male | Calm |
| `am_eric` | Male | Deeper tone |
