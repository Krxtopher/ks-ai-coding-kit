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
| `ELEVENLABS_MODEL_ID` | TTS model | `eleven_multilingual_v2` |

## CLI Options

```bash
# Speak a message (non-blocking)
python3 scripts/speak.py --background --message "Hello world"

# Use a specific voice
python3 scripts/speak.py -b --message "Hello" --voice "pNInz6obpgDQGcFmaJgB"

# Adjust speed (0.5 = slow, 2.0 = fast)
python3 scripts/speak.py -b --message "Hello" --speed 1.1

# Control latency optimization (0=none, 4=max, default=2)
python3 scripts/speak.py -b --message "Hello" --latency 3

# Wait for playback to finish (blocking mode)
python3 scripts/speak.py --message "Hello world"

# Pipe text via stdin
echo "Hello world" | python3 scripts/speak.py -b

# Save current settings to config.json
python3 scripts/speak.py -b --message "Hello" --voice "abc123" --speed 1.1 --save

# Show saved configuration
python3 scripts/speak.py --show-config
```

## Configuration

The script reads `config.json` from the skill root directory. Users create/update it with the `--save` flag. Fields:

```json
{
  "voice_id": "JBFqnCBsd6RMkjVDRZzb",
  "model_id": "eleven_multilingual_v2",
  "speed": 1.0,
  "stability": 0.5,
  "similarity_boost": 0.75,
  "style": 0.0,
  "latency": 2
}
```

Resolution order for each setting: CLI flag > config.json > environment variable > built-in default.

## Available Voices

| Voice ID | Name | Style |
|----------|------|-------|
| `JBFqnCBsd6RMkjVDRZzb` | George | Warm, conversational (default) |
| `pNInz6obpgDQGcFmaJgB` | Adam | Deep, authoritative |
| `ErXwobaYiN019PkySvjV` | Antoni | Young, friendly |
| `VR6AewLTigWG4xSOukaG` | Arnold | Confident, energetic |
| `onwK4e9ZLuTAKqWW03F9` | Daniel | British, warm |
| `TX3LPaxmHKxFdv7VOQHJ` | Liam | American, natural |

Browse all voices at https://elevenlabs.io/voice-library or use the Voices API to list your own cloned voices.

## Cost Awareness

ElevenLabs charges 1 credit per character. Keep narration brief to conserve credits:
- A typical 150-character utterance costs 150 credits
- The Creator plan (100k credits/month) supports roughly 50–100 sessions
- Monitor usage at https://elevenlabs.io/app/usage
