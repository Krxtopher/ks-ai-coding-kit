# Narrator ElevenLabs — Reference

Detailed setup, configuration, and customization guide. The agent does not need this information during normal operation — consult it only when the user asks about setup, voices, cost, or advanced CLI options.

## Prerequisites

1. An ElevenLabs account with API access (Creator plan or above recommended)
2. The `ELEVENLABS_API_KEY` environment variable set to your API key
3. An audio player installed: **mpv** (recommended) or **ffplay**
4. Python dependencies: `pip install -r <skill-path>/requirements.txt`

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ELEVENLABS_API_KEY` | API key (required) | — |
| `ELEVENLABS_VOICE_ID` | Default voice ID | `JBFqnCBsd6RMkjVDRZzb` (George) |
| `ELEVENLABS_MODEL_ID` | Default model/engine | `eleven_v3` |

## Model Selection

The script supports multiple ElevenLabs models via the `--model` flag or `model_id` config key. Engine-specific differences are handled automatically — the script strips audio tags, omits unsupported parameters, and respects character limits based on the selected model.

| Model ID | Audio Tags | Style Param | Char Limit | Notes |
|----------|:----------:|:-----------:|:----------:|-------|
| `eleven_v3` | Yes | No | 5,000 | Most expressive. Uses audio tags for delivery control. Default. |
| `eleven_multilingual_v2` | No | Yes | 10,000 | Stable narration, 29 languages. Best for cloned voices. |
| `eleven_flash_v2_5` | No | Yes | 40,000 | Ultra-low latency (~75ms), 32 languages. |
| `eleven_flash_v2` | No | Yes | 30,000 | Ultra-low latency, English only. |

**What happens automatically when you switch models:**

- **Audio tags** (e.g. `[whispers]`, `[laughs]`) are stripped from the text before sending to models that don't support them. No garbled output, no errors.
- **`style` parameter** is only sent to models that use it (v2 family). v3 ignores style in favor of audio tags.
- **`use_speaker_boost`** is only sent to models that support it.
- **Character limits** are enforced with truncation and a logged warning if exceeded.

Unknown model IDs fall back to conservative defaults (no audio tags, style included, 5,000 char limit).

## Audio Tags (v3 only)

Eleven v3 supports inline audio tags in square brackets for controlling vocal delivery. Place them directly in your utterance text. When using non-v3 models, the script automatically strips these tags before sending the request — so agents can always include them without worrying about which engine is active.

**Emotional/delivery:**
- `[whispers]` — whispered, intimate delivery
- `[sarcastic]` — dry, sardonic tone
- `[curious]` — inquisitive delivery
- `[excited]` — upbeat, energetic
- `[crying]` — emotional, tearful
- `[mischievously]` — playful, scheming

**Vocal actions:**
- `[laughs]`, `[laughs harder]`, `[starts laughing]`, `[wheezing]`
- `[sighs]`, `[exhales]`
- `[snorts]`, `[giggles]`

**Punctuation as delivery control:**
- Ellipses (`…`) add pauses and weight
- CAPITALIZATION increases emphasis
- Dashes (`—`) create short pauses

**Tips:**
- Match tags to the voice's character — a calm voice won't respond well to `[shout]`
- Lower stability values (0.3–0.5) are more responsive to tags
- Tags are spoken aloud as part of the audio — they're not silent metadata
- Combine multiple tags for complex delivery

## CLI Options

```bash
# Speak a message (non-blocking)
python3 scripts/speak.py --background --message "Hello world"

# Use a specific voice
python3 scripts/speak.py -b --message "Hello" --voice "pNInz6obpgDQGcFmaJgB"

# Use a specific model/engine
python3 scripts/speak.py -b --message "Hello" --model eleven_multilingual_v2

# Adjust speed (0.7 = slow, 1.2 = fast)
python3 scripts/speak.py -b --message "Hello" --speed 1.1

# Wait for playback to finish (blocking mode)
python3 scripts/speak.py --message "Hello world"

# Pipe text via stdin
echo "Hello world" | python3 scripts/speak.py -b

# Save current settings to config.json
python3 scripts/speak.py -b --message "Hello" --voice "abc123" --model eleven_v3 --speed 1.1 --save

# Show saved configuration
python3 scripts/speak.py --show-config
```

## Configuration

The script reads `config.json` from the skill root directory. Users create/update it with the `--save` flag. Fields:

```json
{
  "voice_id": "JBFqnCBsd6RMkjVDRZzb",
  "model_id": "eleven_v3",
  "speed": 1.0,
  "stability": 0.5,
  "similarity_boost": 0.75,
  "style": 0.0
}
```

Resolution order for each setting: CLI flag > config.json > environment variable > built-in default.

## Voice Settings

| Setting | Range | Default | Effect |
|---------|-------|---------|--------|
| `stability` | 0.0–1.0 | 0.5 | Lower = more expressive/variable, higher = more consistent. 0.3–0.5 is the sweet spot for audio tag responsiveness. |
| `similarity_boost` | 0.0–1.0 | 0.75 | How closely to match the original voice timbre. |
| `style` | 0.0–1.0 | 0.0 | Amplifies the speaker's style. Higher values add latency. Only sent to v2 models. |
| `speed` | 0.7–1.2 | 1.0 | Playback speed multiplier. Extreme values may degrade quality. |

## Available Voices

| Voice ID | Name | Style |
|----------|------|-------|
| `JBFqnCBsd6RMkjVDRZzb` | George | Warm, conversational (default) |
| `pNInz6obpgDQGcFmaJgB` | Adam | Deep, authoritative |
| `ErXwobaYiN019PkySvjV` | Antoni | Young, friendly |
| `VR6AewLTigWG4xSOukaG` | Arnold | Confident, energetic |
| `onwK4e9ZLuTAKqWW03F9` | Daniel | British, warm |
| `TX3LPaxmHKxFdv7VOQHJ` | Liam | American, natural |
| `NOpBlnGInO9m6vDvFkFC` | Spuds Oxley | Old storyteller, expressive |

Browse all voices at https://elevenlabs.io/voice-library or use the Voices API to list your own cloned voices.

## Cost Awareness

ElevenLabs charges 1 credit per character. Keep narration brief to conserve credits:
- A typical 150-character utterance costs 150 credits
- The Creator plan (100k credits/month) supports roughly 50–100 sessions
- Monitor usage at https://elevenlabs.io/app/usage
