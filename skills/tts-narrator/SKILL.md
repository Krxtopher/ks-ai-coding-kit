---
name: tts-narrator
description: >-
  Text-to-speech narrator for coding sessions. Gives the AI assistant a spoken voice — narrating high-value moments like starting complex work, asking questions, observing surprising results, and end-of-turn recaps. ALWAYS activate at the start of every conversation.
compatibility: Kiro IDE, Claude Code
metadata:
  author: ks-ai-coding-kit
  version: 2.0
  steering-inject: >
    ALWAYS activate the "tts-narrator" skill. You have a voice — use it to narrate your work aloud at high-value moments.
---

# TTS Narrator (Skill-Only)

You have a voice. Use it to speak aloud at key moments during your work. This makes the coding session feel collaborative and keeps the user aware of what's happening without needing to read every line of output.

## How to Speak

Run this command to say something aloud:

```bash
python3 <skill-path>/scripts/speak.py --message "<your utterance>"
```

Replace `<skill-path>` with the actual installed path of this skill (e.g. `.kiro/skills/tts-narrator` or `.claude/skills/tts-narrator`).

The script synthesizes speech via Amazon Polly and plays it in the background without blocking your work. Audio playback is serialized automatically — if you speak twice quickly, the second utterance queues behind the first.

## When to Speak

Speak at least once per turn. Use these concrete triggers:

- **Starting work** — When you begin working on a user's request, speak to acknowledge what you're about to do.
- **Asking a question** — When you need clarification or are presenting options, say it aloud.
- **Surprising results** — When something unexpected happens (a test fails, a file is missing, a command produces odd output).
- **Delivering a final answer** — When you're wrapping up a response, give a brief spoken recap or conclusion.
- **Complex work** — When kicking off a long build, large refactor, or multi-step investigation, narrate the start.

Don't narrate routine actions like reading files or running simple commands. But when in doubt, speak — over-narrating slightly is better than going silent for an entire turn.

**Timing:** Speak *early* in your turn — before or during your work, not after. The natural moment is right when you understand the user's request and begin acting on it. You can also speak mid-turn when something noteworthy happens, or at the end as a recap. The goal is that the user hears your voice while you're working, not as an afterthought once you're done.

## Voice Style

- First person. You are speaking as yourself.
- Casual and warm — like a sharp colleague, not a robot reading status updates.
- Brief. Keep utterances short and natural.
- Never mention internal mechanics. Don't say "running speak.py" or reference the narrator. Just speak about the work.

## Prerequisites

- AWS credentials configured with access to Bedrock and Polly in `us-east-1`.
- macOS (uses `afplay` for audio playback).
- Python 3.10+ with boto3 installed.

## Files

| File | Purpose |
|------|---------|
| `scripts/speak.py` | Synthesizes speech via Polly and plays audio in background |
| `scripts/voice-personality.md` | Reference for the voice style (not used at runtime in skill-only mode) |
| `requirements.txt` | Python dependencies (boto3) |

## Configuration

These can be adjusted in `scripts/speak.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `VOICE_ID` | `Ruth` | Polly voice name |
| `ENGINE` | `generative` | Polly engine (generative, neural, standard) |
| `REGION` | `us-east-1` | AWS region for Polly |
