# Podcast ElevenLabs

Turn any text content into a polished two-voice audio podcast using ElevenLabs' expressive TTS engine. Feed it a summary of an article, a document, meeting notes, a changelog — anything — and it produces a conversational MP3 episode with natural emotional delivery, complete with intro/outro music.

## How It Works

1. **You provide content** — A plain-text summary of whatever you want turned into a podcast.
2. **Script generation** — Amazon Bedrock (Claude) converts the summary into a natural two-presenter dialogue script, including ElevenLabs audio tags for expressive delivery.
3. **Speech synthesis** — ElevenLabs v3 turns each dialogue turn into emotionally expressive speech, responding to audio tags like `[excited]`, `[laughs]`, and `[thoughtful]`.
4. **Audio mixing** — Intro music fades in, ducks under a spoken intro, the conversation plays, then outro music wraps it up.

All outputs (config, content, script, and audio) are saved to a timestamped folder for reproducibility.

## Implementation Status

## Model Selection

The `--elevenlabs-model` flag controls which ElevenLabs model is used for synthesis:

| Model ID | Audio Tags | Best For |
|----------|-----------|----------|
| `eleven_v3` (default) | Supported | Maximum expressiveness, emotional range |
| `eleven_multilingual_v2` | Stripped automatically | Multilingual content, stability |
| `eleven_flash_v2_5` | Stripped automatically | Low latency, high throughput |

When a v2 model is selected, audio tags like `[excited]` and `[laughs]` are automatically removed from the script text before sending to the API — no manual editing needed.

## Prerequisites

- **Python 3.10+**
- **[ffmpeg](https://ffmpeg.org/)** installed and on your PATH (required by pydub)
- **ElevenLabs API key** — set `ELEVENLABS_API_KEY` env var or pass via `--api-key`
- **AWS credentials** with access to Amazon Bedrock (for script generation via Claude)
- For Python 3.13+: install `audioop-lts` for pydub compatibility

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your ElevenLabs API key
export ELEVENLABS_API_KEY="your-key-here"

# 3. Write or generate a content summary
echo "Your content summary goes here..." > my_summary.txt

# 4. Generate the podcast (run from the skill root directory)
python scripts/generate_podcast.py generate \
  --content-file my_summary.txt \
  --title "My Episode" \
  --intro-music assets/music.mp3

# 5. Listen (path shown in the output)
afplay output/20260712-1400_my-episode/podcast.mp3
```

## Subcommands

### `generate` — Full pipeline

```bash
python scripts/generate_podcast.py generate \
  --content-file article_summary.txt \
  --title "AI in Healthcare" \
  --voice1 Brian \
  --voice2 Sarah \
  --duration 3.0 \
  --stability 0.4 \
  --intro-music assets/music.mp3
```

### `script` — Script generation only

Generates the podcast script with ElevenLabs audio tags without synthesizing audio.

```bash
python scripts/generate_podcast.py script \
  --content-file notes.txt \
  --title "Sprint Recap" \
  --duration 2.0
```

### `synthesize` — Audio from existing script

Re-generates audio from a previously created run directory.

```bash
python scripts/generate_podcast.py synthesize \
  --run-dir output/20260712-1400_sprint-recap/ \
  --voice1 George \
  --stability 0.3
```

## Audio Tags

The script generator automatically includes ElevenLabs v3 audio tags in the dialogue for expressive performance:

```json
[
  {"speaker": "voice1", "text": "Hey, so this is a really interesting one..."},
  {"speaker": "voice2", "text": "[excited] Yeah, I was reading through this and it totally changed how I think about it."},
  {"speaker": "voice1", "text": "OK so break it down for me — what's the big takeaway?"},
  {"speaker": "voice2", "text": "[thoughtful] Well... the core idea is actually pretty simple once you see it."}
]
```

Supported tags include: `[excited]`, `[thoughtful]`, `[surprised]`, `[curious]`, `[amused]`, `[laughs]`, `[sighs]`, `[chuckles]`, and more.

## Directory Structure

```
skills/podcast-elevenlabs/
├── SKILL.md                 # Agent skill definition
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── generate_podcast.py  # Main orchestrator and CLI
│   ├── scriptgen.py         # LLM script generation (Bedrock)
│   ├── synthesize.py        # ElevenLabs TTS synthesis
│   ├── mixer.py             # Audio mixing (pydub/ffmpeg)
│   └── voices.py            # ElevenLabs voice registry
├── assets/                  # Music files and text templates
│   ├── music.mp3            # Default intro/outro music
│   ├── prompt_template.txt  # LLM prompt template (with audio tag instructions)
│   ├── voice1_personality.txt
│   ├── voice2_personality.txt
│   ├── intro_speech.txt
│   └── outro_speech.txt
└── output/                  # Generated podcast runs (created at runtime)
```

## Voice Settings

ElevenLabs provides fine-grained control over voice delivery:

| Setting | Range | Default | Effect |
|---------|-------|---------|--------|
| `--stability` | 0.0–1.0 | 0.5 | Lower = more expressive and varied |
| `--similarity-boost` | 0.0–1.0 | 0.75 | Higher = closer to original voice |
| `--style` | 0.0–1.0 | 0.0 | Higher = more stylistic exaggeration |
| `--speed` | 0.7–1.2 | 1.0 | Speech speed multiplier |

For podcast-style conversational delivery, try `--stability 0.3` to `0.5` for natural emotional range.

## Customization

### Host personalities

Edit `assets/voice1_personality.txt` and `assets/voice2_personality.txt` to change how each presenter behaves in the conversation. These are plain-text descriptions injected into the LLM prompt.

You can also override personalities per-run via CLI flags:

```bash
python scripts/generate_podcast.py generate \
  --content-file summary.txt \
  --voice1-personality "A skeptical journalist who challenges every claim"
```

### Prompt template

Edit `assets/prompt_template.txt` to change the podcast style, tone, structure, or turn count. This template includes ElevenLabs audio tag instructions.

### Intro/outro speech

Edit `assets/intro_speech.txt` and `assets/outro_speech.txt` to customize the spoken intro and sign-off. The intro supports `{title}`, `{voice1_name}`, and `{voice2_name}` placeholders. Multi-line intro files produce one synthesized segment per line.

You can also override per-run:

```bash
python scripts/generate_podcast.py generate \
  --content-file summary.txt \
  --intro-speech "Welcome to today's deep dive on {title}. I'm {voice1_name}." \
  --outro-speech "Thanks for listening. See you next time."
```

## Notes

- ElevenLabs v3 produces highly expressive speech that responds to audio tags in the text.
- Audio normalization (EBU R128, -14 LUFS) is enabled by default for broadcast-standard loudness. Disable with `--no-normalize`.
- The `stability` slider is the most impactful setting — "Creative" (low) enables more emotional range.
- Custom Instant Voice Clones (IVCs) work well with v3; Professional Voice Clones (PVCs) are still being optimized.
- Target duration is approximate — actual length depends on speaking pace and turn count.
- The prompt template at `assets/prompt_template.txt` can be customized to change podcast style.
- Host personalities are defined in `assets/voice1_personality.txt` and `assets/voice2_personality.txt` — edit these to change presenter behavior without touching the prompt template.
- Personalities can also be overridden per-run via `--voice1-personality` and `--voice2-personality` (accepts inline text or a path to a .txt file).
- Intro and outro speech can be overridden per-run via `--intro-speech` and `--outro-speech` (accepts inline text or a path to a .txt file). The intro speech supports `{title}`, `{voice1_name}`, and `{voice2_name}` template variables.
- The default Bedrock model is `us.anthropic.claude-opus-4-6-v1`; use `--bedrock-model` to override.
