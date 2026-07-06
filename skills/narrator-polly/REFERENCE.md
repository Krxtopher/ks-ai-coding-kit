# Narrator Polly — Reference

Detailed setup, configuration, and customization guide. The agent does not need this information during normal operation — consult it only when the user asks about setup, voices, cost, or advanced CLI options.

## Prerequisites

1. AWS credentials configured (via `~/.aws/config`, environment variables, or IAM role)
2. IAM permissions for `polly:SynthesizeSpeech` (the `AmazonPollyReadOnlyAccess` managed policy works)
3. An audio player installed: **mpv** (recommended) or **ffplay** — used by `speak.py` for streaming TTS playback
4. Python dependencies: `pip install -r <skill-path>/requirements.txt`

> [!NOTE]
> The cold open orchestrator (`orchestrate_open.py`) uses `sounddevice` for real-time audio mixing and does not require an external player. Only `speak.py` (single-utterance narration) still pipes to mpv/ffplay.

## No API Key Required

Unlike third-party TTS services, Amazon Polly uses your existing AWS credentials. If you can run `aws sts get-caller-identity` successfully, you're ready to go. No separate API key signup or environment variable is needed.

## CLI Options

```bash
# Speak a message (non-blocking)
python3 scripts/speak.py --background --message "Hello world"

# Use a specific voice
python3 scripts/speak.py -b --message "Hello" --voice "Ruth"

# Adjust speed
python3 scripts/speak.py -b --message "Hello" --speed fast

# Use a different AWS region
python3 scripts/speak.py -b --message "Hello" --region us-west-2

# Wait for playback to finish (blocking mode)
python3 scripts/speak.py --message "Hello world"

# Pipe text via stdin
echo "Hello world" | python3 scripts/speak.py -b

# Save current settings to config.json
python3 scripts/speak.py -b --message "Hello" --voice "Stephen" --speed fast --save

# Show saved configuration
python3 scripts/speak.py --show-config

# Debug mode: write audio and request payload to debug/ directory
python3 scripts/speak.py --debug --message "Test utterance"
```

## Configuration

The script reads `config.json` from the skill root directory. This file is the single source of truth for all narrator settings. Users can create/update it with the `--save` flag or edit it directly.

All available fields:

```json
{
  "personality": "default",
  "voice_id": "Ruth",
  "speed": "medium",
  "region": "us-west-2",
  "endpoint_url": null,
  "profile": null,
  "debug": false
}
```

| Field | Purpose | Default |
|-------|---------|---------|
| `personality` | Active personality (folder name under `personalities/`) | `default` |
| `voice_id` | Polly voice ID (standard or cloned) | `Ruth` |
| `speed` | Prosody rate: x-slow, slow, medium, fast, x-fast | `medium` |
| `region` | AWS region for Polly API calls | `us-west-2` |
| `endpoint_url` | Custom Polly endpoint (e.g. gamma for voice cloning) | Standard endpoint |
| `profile` | AWS credential profile name | Default profile |
| `debug` | Write audio and request payload to `debug/` directory | `false` |

Resolution order for each setting: **CLI flag > config.json > built-in default**.

### Example: Standard Voice (Ruth)

```json
{
  "voice_id": "Ruth",
  "speed": "medium",
  "region": "us-west-2"
}
```

### Example: Cloned Voice (via gamma endpoint)

```json
{
  "personality": "tal-parody",
  "voice_id": "vc-56f8fbd479",
  "speed": "medium",
  "region": "us-east-1",
  "endpoint_url": "https://gamma.us-east-1.parrot.a2z.com/",
  "profile": "polly-shared"
}
```

## Personalities

Personalities define how the narrator speaks — tone, style, and optional orchestrated cold opens. Each personality lives in its own subdirectory under `personalities/`:

```
personalities/
├── default/
│   └── personality.md
└── tal-parody/
    ├── personality.md
    ├── cold-open.yaml        (optional)
    └── cold-open-music.mp3   (optional, referenced by cold-open.yaml)
```

### Structure

Each personality folder contains:

| File | Required | Purpose |
|------|----------|---------|
| `personality.md` | Yes | Defines voice style, tone, structural beats, and SSML preferences |
| `cold-open.yaml` | No | Orchestrated session opener with music and TTS sequencing |
| `cold-open-music.mp3` | No | Music file for the cold open (referenced by `cold-open.yaml`) |

### Switching Personalities

Change the `personality` value in `config.json` to the folder name of the desired personality:

```json
{
  "personality": "tal-parody"
}
```

### Creating a New Personality

1. Create a new folder under `personalities/` (e.g. `personalities/my-style/`)
2. Add a `personality.md` describing the voice style
3. Optionally add `cold-open.yaml` and `cold-open-music.mp3` for an orchestrated session opener
4. Update `config.json` to point to the new folder name

## Available Generative Voices (English)

These are the voices available with Polly's generative engine for English:

| Voice ID | Language | Gender | Style |
|----------|----------|--------|-------|
| Ruth | en-US | Female | Calm, composed (default) |
| Matthew | en-US | Male | Warm, conversational |
| Stephen | en-US | Male | Clear, professional |
| Danielle | en-US | Female | Natural, friendly |
| Joanna | en-US | Female | Clear, versatile |
| Salli | en-US | Female | Warm, expressive |
| Tiffany | en-US | Female | Bright, youthful |
| Amy | en-GB | Female | British, clear |
| Brian | en-GB | Male | British, authoritative |
| Olivia | en-AU | Female | Australian, warm |
| Kajal | en-IN | Female | Indian English, clear |
| Niamh | en-IE | Female | Irish, melodic |
| Aria | en-NZ | Female | New Zealand, natural |

For a full list of all generative voices across all languages, see: https://docs.aws.amazon.com/polly/latest/dg/generative-voices.html

## Speed Options

The `--speed` flag maps to SSML prosody rates:

| Value | Effect |
|-------|--------|
| `x-slow` | Very slow, deliberate |
| `slow` | Slightly slower than natural |
| `medium` | Natural pace (default) |
| `fast` | Slightly faster than natural |
| `x-fast` | Very fast, energetic |

## SSML Tags (Generative Engine)

The following SSML tags are supported with generative voices:

| Tag | Availability | Notes |
|-----|-------------|-------|
| `<break>` | Full | Pause control (e.g., `<break time="500ms"/>`) |
| `<lang>` | Full | Specify language for foreign words |
| `<p>` / `<s>` | Full | Paragraph and sentence boundaries |
| `<prosody>` | Partial | Rate and volume (pitch control limited) |
| `<say-as>` | Full | Control interpretation (characters, date, etc.) |
| `<sub>` | Full | Pronunciation substitution |
| `<w>` | Full | Part-of-speech hints |

**Not supported with generative engine:** `<emphasis>`, `<amazon:auto-breaths>`, `<amazon:effect>` (whisper, DRC, vocal-tract-length), `<amazon:domain>`.

## Cost

Amazon Polly generative engine pricing: **$30 per 1 million characters**.

For narrator usage with short utterances (50–200 characters each):
- 100 utterances/day at ~100 chars each = 10,000 chars/day = **$0.30/day**
- A typical coding session (20–40 utterances) costs roughly **$0.06–$0.12**
- Monthly cost for daily use: approximately **$6–$9**

There is no free tier for generative voices. Standard voices ($4/M chars) and neural voices ($16/M chars) are available at lower cost but with less natural delivery.

## Supported Regions

Polly's generative engine is available in select regions. The default is `us-west-2`.

- `us-west-2` (Oregon) — recommended, default
- `us-east-1` (N. Virginia)
- `eu-west-1` (Ireland)
- `eu-central-1` (Frankfurt)
- `ap-northeast-1` (Tokyo)
- `ap-southeast-1` (Singapore)
- `ap-northeast-2` (Seoul)
- `ca-central-1` (Canada)
- `eu-west-2` (London)
- `eu-central-2` (Zurich)

> [!NOTE]
> If you get empty audio or `IncompleteRead` errors in a particular region, try switching to a different one. Region availability for generative voices can vary.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No audio player found" | Install mpv (`brew install mpv`) or ffplay (part of ffmpeg) |
| "AccessDeniedException" | Ensure your IAM role/user has `polly:SynthesizeSpeech` permission |
| "InvalidEngine" | Verify the voice supports generative engine, or try a different region |
| Audio plays but sounds robotic | Confirm `Engine=generative` is being used (not standard or neural) |
| Playback has high latency | Try a closer AWS region, or switch to mpv if using ffplay |
