# Podcast Polly

Turn any text content into a polished two-voice audio podcast using Amazon Polly's generative TTS engine. Feed it a summary of an article, a document, meeting notes, a changelog — anything — and it produces a conversational MP3 episode complete with intro/outro music.

## How It Works

1. **You provide content** — A plain-text summary of whatever you want turned into a podcast.
2. **Script generation** — Amazon Bedrock (Claude) converts the summary into a natural two-presenter dialogue script.
3. **Speech synthesis** — Amazon Polly's generative engine turns each dialogue turn into high-quality speech audio.
4. **Audio mixing** — Intro music fades in, ducks under a spoken intro, the conversation plays, then outro music wraps it up.

All outputs (config, content, script, and audio) are saved to a timestamped folder for reproducibility.

## Prerequisites

- **Python 3.10+**
- **[ffmpeg](https://ffmpeg.org/)** installed and on your PATH (required by pydub)
- **AWS credentials** with access to:
  - Amazon Bedrock (for script generation via Claude)
  - Amazon Polly generative engine (for TTS synthesis)
- For cloned voices or beta features: pass a custom Polly endpoint URL via `--polly-endpoint`
- For Python 3.13+: install `audioop-lts` for pydub compatibility

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Write or generate a content summary
echo "Your content summary goes here..." > my_summary.txt

# 3. Generate the podcast (run from the skill root directory)
python scripts/generate_podcast.py generate --content-file my_summary.txt --title "My Episode"

# 4. Listen (path shown in the output)
afplay output/20260712-1400_my-episode/podcast.mp3
```

## Subcommands

### `generate` — Full pipeline

Runs the complete workflow: script generation, audio synthesis, and mixing.

```bash
python scripts/generate_podcast.py generate \
  --content-file article_summary.txt \
  --title "AI in Healthcare" \
  --voice1 Ruth \
  --voice2 Kenneth \
  --duration 3.0 \
  --intro-music assets/music.mp3 \
  --music-volume 60
```

### `script` — Script generation only

Generates the podcast script without synthesizing audio. Useful for reviewing or editing the script before committing to synthesis.

```bash
python scripts/generate_podcast.py script \
  --content-file notes.txt \
  --title "Sprint Recap" \
  --duration 2.0
```

### `synthesize` — Audio from existing script

Re-generates audio from a previously created run directory. Lets you change voices, music, or other settings without re-running script generation.

```bash
python scripts/generate_podcast.py synthesize \
  --run-dir output/20260712-1400_sprint-recap/ \
  --voice1 Matthew \
  --intro-music assets/music.mp3 \
  --music-volume 80
```

## Output Structure

Every run creates a self-contained folder under `output/`:

```
output/20260712-1400_my-episode/
├── config.json      # Full configuration used for the run
├── content.txt      # Content summary that was provided
├── script.json      # Generated podcast script
└── podcast.mp3      # Final mixed audio
```

## Directory Structure

```
skills/podcast-polly/
├── SKILL.md                 # Agent skill definition
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── generate_podcast.py  # Main orchestrator and CLI
│   ├── scriptgen.py         # LLM script generation (Bedrock)
│   ├── synthesize.py        # Polly TTS synthesis
│   ├── mixer.py             # Audio mixing (pydub/ffmpeg)
│   └── voices.py            # Polly voice registry
├── assets/                  # Music files and text templates
│   ├── music.mp3            # Default intro/outro music
│   ├── prompt_template.txt  # LLM prompt template
│   ├── voice1_personality.txt  # Default personality for voice 1
│   ├── voice2_personality.txt  # Default personality for voice 2
│   ├── intro_speech.txt     # Spoken intro template
│   └── outro_speech.txt     # Spoken outro text
└── output/                  # Generated podcast runs (created at runtime)
```

## Available Voices

| Name | Language | Gender |
|------|----------|--------|
| Matthew | en-US | Male |
| Danielle | en-US | Female |
| Ruth | en-US | Female |
| Kenneth | en-US | Male |
| Tiffany | en-US | Feminine |
| Olivia | en-AU | Feminine |
| Amy | en-GB | Feminine |
| Kiara | en-IN | Feminine |
| Arjun | en-IN | Masculine |

You can also pass any raw Polly voice ID directly (e.g. `--voice1 vc-56f8fbd479` for a cloned voice).

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

Edit `assets/prompt_template.txt` to change the podcast style, tone, structure, or turn count.

### Intro/outro speech

Edit `assets/intro_speech.txt` and `assets/outro_speech.txt` to customize the spoken intro and sign-off. The intro supports `{title}`, `{voice1_name}`, and `{voice2_name}` placeholders.

## Notes

- The generative engine produces the most natural-sounding voices available in Polly.
- At beta rate limits (~1 TPS), synthesis is sequential. Each segment takes 1-4 seconds.
- A 2-minute podcast typically takes 30-60 seconds to generate end-to-end.
- The word budget is automatically calculated from `--duration` minus intro/outro time.
- The default Bedrock model is `us.anthropic.claude-opus-4-6-v1`; use `--model` to override.
