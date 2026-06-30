---
name: tts-narrator
description: >-
  Text-to-speech narrator for Kiro IDE sessions using Amazon Bedrock and Amazon Polly.
  Provides spoken voice feedback during coding sessions — narrating actions, flagging
  surprises, and recapping work. Companion to the tts-narrator hooks.
compatibility: Kiro IDE
metadata:
  author: ks-ai-coding-kit
  version: 1.0
---

# TTS Narrator

Gives Kiro a voice using Amazon Bedrock (for utterance generation) and Amazon Polly (for speech synthesis). Works alongside the tts-narrator hooks to provide spoken feedback during coding sessions.

## How It Works

The hooks (installed separately) trigger `scripts/speak.py` at key moments:
- **Pre-shell**: Before a shell command runs, Kiro says what it's about to do.
- **Post-shell**: After a command finishes, Kiro speaks only if something unexpected happened.
- **Agent stop**: At the end of a turn, Kiro recaps or voices a question.

## Files

| File | Purpose |
|------|---------|
| `scripts/speak.py` | Main script — generates utterances via Bedrock, synthesizes via Polly, plays audio |
| `scripts/voice-personality.md` | The voice personality prompt — edit this to change how Kiro sounds |
| `requirements.txt` | Python dependencies (boto3) |

## Customizing the Voice

Edit `scripts/voice-personality.md` to change Kiro's speaking style, personality, tone, or behavior rules. This file is the system prompt sent to the LLM when generating what to say. No code changes needed.

## Configuration

The following can be adjusted in `scripts/speak.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_ID` | `us.amazon.nova-micro-v1:0` | Bedrock model for utterance generation |
| `VOICE_ID` | `Ruth` | Polly voice name |
| `ENGINE` | `generative` | Polly engine (generative, neural, standard) |
| `REGION` | `us-east-1` | AWS region for Bedrock and Polly |

## Prerequisites

- AWS credentials configured with access to Bedrock and Polly in the configured region.
- macOS (uses `afplay` for audio playback).
- Python 3.10+ with boto3 installed.

## Companion Hooks

This skill is designed to work with the tts-narrator hooks (installed separately from the hooks catalog). The hooks call `speak.py` at the right moments — the skill provides the brains and voice.
