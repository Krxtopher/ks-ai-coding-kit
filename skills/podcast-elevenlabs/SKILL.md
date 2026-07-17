---
name: podcast-elevenlabs
description: Transforms any text content into a polished multi-voice audio podcast using Amazon Bedrock for script generation and ElevenLabs for expressive speech synthesis with audio tag direction.
---

# Podcast ElevenLabs

Generate a two-voice conversational podcast from any content summary. The agent gathers and summarizes the source material; this skill handles script writing, audio synthesis via ElevenLabs, and mixing.

This skill leverages ElevenLabs v3's audio tag system to produce expressive, emotionally nuanced speech — including laughter, whispers, excitement, and natural reactions that bring the conversation to life.

## When to Use

- User asks to create a podcast, audio summary, or audio briefing from any content
- User wants to turn a document, article, changelog, meeting notes, or research into audio
- User requests a "listen-friendly" version of written content
- User wants to regenerate audio from an existing script (different voices, settings, etc.)
- User specifically requests ElevenLabs voices or expressive/emotional delivery

## Workflow

1. **Gather content** — Use your tools (web fetch, file read, API calls) to collect the source material the user wants turned into a podcast.
2. **Summarize** — Produce a plain-text content summary (1000–3000 words) structured with clear sections and bullet points. Include enough detail for an engaging conversation but not so much that it overwhelms the script generator.
3. **Invoke the skill** — Call `scripts/generate_podcast.py` with a subcommand and the appropriate options.

## Subcommands

### `generate` — Full pipeline

Runs the complete workflow: script generation, audio synthesis, and mixing.

```bash
python scripts/generate_podcast.py generate \
  --content-file <path_to_summary.txt> \
  --title "Episode Title" \
  --voice1 George \
  --voice2 Rachel \
  --duration 2.0 \
  --intro-music assets/music.mp3 \
  --music-volume 60 \
  --api-key $ELEVENLABS_API_KEY
```

### `script` — Script generation only

Generates the podcast script without synthesizing audio. The script will include ElevenLabs audio tags for expressive delivery.

```bash
python scripts/generate_podcast.py script \
  --content-file <path_to_summary.txt> \
  --title "Episode Title" \
  --duration 2.0
```

### `synthesize` — Audio from existing script

Synthesizes audio from an existing run directory's `script.json`. Allows re-generating audio with different voices or settings without re-running script generation.

```bash
python scripts/generate_podcast.py synthesize \
  --run-dir output/20260712-1841_episode-title/ \
  --voice1 Brian \
  --stability 0.3 \
  --api-key $ELEVENLABS_API_KEY
```

## Output Structure

All artifacts are saved to a timestamped folder under `output/`:

```
output/20260712-1841_episode-title/
├── config.json      # Full configuration used for the run
├── content.txt      # Content summary that was used
├── script.json      # Generated podcast script (with audio tags)
└── podcast.mp3      # Final mixed audio (after synthesis)
```

The folder name format is: `YYYYMMDD-HHMM_<slugified-title>`

## Parameters

### Shared parameters (all subcommands with content)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--content` | One of content/content-file | — | Inline content summary text |
| `--content-file` | One of content/content-file | — | Path to a text file with the content summary |
| `--title` | No | "Podcast" | Episode title (used in intro speech and folder name) |
| `--voice1` | No | `George` | Lead presenter voice (name or ElevenLabs voice ID) |
| `--voice2` | No | `Rachel` | Co-presenter voice (name or ElevenLabs voice ID) |
| `--voice1-name` | No | *(inferred)* | Display name for voice 1 in dialogue |
| `--voice2-name` | No | *(inferred)* | Display name for voice 2 in dialogue |
| `--voice1-personality` | No | `assets/voice1_personality.txt` | Personality description for voice 1 (inline text or path to .txt file) |
| `--voice2-personality` | No | `assets/voice2_personality.txt` | Personality description for voice 2 (inline text or path to .txt file) |
| `--intro-speech` | No | `assets/intro_speech.txt` | Custom intro speech (inline text or path to .txt file). Supports `{title}`, `{voice1_name}`, `{voice2_name}` placeholders. Multi-line files produce one segment per line. |
| `--outro-speech` | No | `assets/outro_speech.txt` | Custom outro speech (inline text or path to .txt file) |
| `--duration` | No | `2.0` | Target duration in minutes |
| `--api-key` | No | `$ELEVENLABS_API_KEY` | ElevenLabs API key (or set env var) |
| `--elevenlabs-model` | No | `eleven_v3` | ElevenLabs model ID |
| `--stability` | No | `0.5` | Voice stability (0.0–1.0). Lower = more expressive |
| `--similarity-boost` | No | `0.75` | Voice clarity/similarity (0.0–1.0) |
| `--style` | No | `0.0` | Style exaggeration (0.0–1.0) |
| `--speed` | No | `1.0` | Speech speed multiplier (0.7–1.2) |
| `--profile` | No | *(default)* | AWS profile for Bedrock (script generation) |
| `--bedrock-model` | No | *(default)* | Override the Bedrock model ID |
| `--thinking` | No | `false` | Enable adaptive thinking for script generation |
| `--intro-music` | No | *(none)* | Path to intro/outro music MP3 |
| `--music-volume` | No | `60` | Music volume percentage (1–100) |
| `--verbose` | No | `false` | Enable verbose logging output |
| `--normalize` | No | `true` | Normalize audio loudness to -14 LUFS (EBU R128 podcast standard). Enabled by default. |
| `--no-normalize` | No | `false` | Disable audio normalization |

### `generate` only

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--script-only` | No | `false` | Generate script and print JSON without synthesizing |

### `synthesize` only

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--run-dir` | Yes | — | Path to existing run directory with script.json |
| `--voice1` | No | *(from config)* | Override voice 1 |
| `--voice2` | No | *(from config)* | Override voice 2 |
| `--intro-music` | No | *(from config)* | Override music file |
| `--music-volume` | No | *(from config)* | Override music volume |
| `--elevenlabs-model` | No | *(from config)* | Override model |
| `--stability` | No | *(from config)* | Override stability |
| `--similarity-boost` | No | *(from config)* | Override similarity boost |
| `--style` | No | *(from config)* | Override style |
| `--speed` | No | *(from config)* | Override speed |
| `--intro-speech` | No | *(from config)* | Override intro speech |
| `--outro-speech` | No | *(from config)* | Override outro speech |

## Typical Agent Workflows

### Full generation (most common)

1. Gather and summarize content to a temp file
2. Run `generate` subcommand with all options
3. Clean up the temp content file
4. Report the output directory to the user

### Iterative workflow

1. Run `script` to generate and review the script (includes audio tags)
2. User reviews `script.json`, optionally edits audio tags or dialogue
3. Run `synthesize --run-dir <path>` to produce audio from the reviewed script

### Re-take with different settings

1. Run `synthesize --run-dir <existing-run> --voice1 Brian --stability 0.3`
2. The new audio replaces `podcast.mp3` in the same run directory

## Content Summary Guidelines

When preparing the content summary for the skill, follow these guidelines:

- **Structure with headers** — Use `##` headers to separate distinct topics or themes
- **Use bullet points** — List specific facts, changes, or insights as bullets
- **Include context** — Add 1–2 sentences explaining what the subject matter is and why it matters
- **Keep it focused** — 1000–3000 words is the sweet spot. Too little = shallow podcast, too much = the LLM ignores details
- **Name sources** — Mention where information came from (article titles, document names) so the presenters can reference them naturally

### Example Summary Structure

```
## Topic: [What this podcast episode covers]

Background: [1-2 sentences of context for listeners unfamiliar with the topic]

## Key Points

- Point 1: [detail]
- Point 2: [detail]
- Point 3: [detail]

## Interesting Details

- [Supporting facts, quotes, or data]
- [Surprising findings or counterpoints]

## Implications

- [What this means for the audience]
- [What to watch for next]
```

## Audio Tags in Scripts

This skill instructs the LLM to include ElevenLabs v3 audio tags in the generated script for expressive delivery:

- **Emotions**: `[excited]`, `[thoughtful]`, `[surprised]`, `[curious]`, `[amused]`
- **Reactions**: `[laughs]`, `[sighs]`, `[chuckles]`
- **Pacing**: Ellipses (`...`) for natural pauses

Tags are used sparingly (1–2 per turn max) and placed before the affected text. Not every turn includes tags — plain dialogue is the default.

## Available Voices

Popular pre-made ElevenLabs voices (a subset — all pre-made voices are supported):

| Name | Gender | Good For |
|------|--------|----------|
| George | Male | Narration, conversational |
| Rachel | Female | Warm, natural |
| Brian | Male | Authoritative, clear |
| Sarah | Female | Friendly, approachable |
| Josh | Male | Young, energetic |
| Emily | Female | Professional |
| Charlie | Male | Casual, relatable |
| Lily | Female | Soft, thoughtful |
| Daniel | Male | Deep, measured |
| Matilda | Female | Expressive |

Any ElevenLabs voice ID can be passed directly (including custom cloned voices).

## Prerequisites

- Python 3.10+
- ffmpeg on PATH
- ElevenLabs API key (set `ELEVENLABS_API_KEY` env var or pass via `--api-key`)
- AWS credentials with Bedrock (Claude) access for script generation
- For Python 3.13+: install `audioop-lts` for pydub compatibility

## Implementation Status

The ElevenLabs synthesis module is fully implemented using the official `elevenlabs` Python SDK. Both v3 (with audio tag support) and v2/v2.5 models (tags stripped automatically) are supported.

## Error Handling

- If Bedrock returns an invalid script, the tool retries once with a simplified prompt
- If synthesis fails, the error is reported with the specific segment and voice ID
- Missing API key surfaces immediately with a clear message

## Notes

- ElevenLabs v3 produces highly expressive speech that responds to audio tags
- The `stability` parameter is the most impactful setting — lower values (0.3–0.5) produce more emotional range
- Custom cloned voices (IVCs) work well with v3; PVCs are not yet fully optimized for v3
- Target duration is approximate — actual length depends on speaking pace and turn count
- The prompt template at `assets/prompt_template.txt` includes audio tag instructions
- Host personalities are defined in `assets/voice1_personality.txt` and `assets/voice2_personality.txt` — edit these to change presenter behavior without touching the prompt template
- Personalities can also be overridden per-run via `--voice1-personality` and `--voice2-personality` (accepts inline text or a path to a .txt file)
- Intro and outro speech can be overridden per-run via `--intro-speech` and `--outro-speech` (accepts inline text or a path to a .txt file). The intro speech supports `{title}`, `{voice1_name}`, and `{voice2_name}` template variables.
- The default Bedrock model is `us.anthropic.claude-opus-4-6-v1`; use `--bedrock-model` to override
