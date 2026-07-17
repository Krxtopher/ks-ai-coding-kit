---
name: podcast-polly
description: Transforms any text content into a polished multi-voice audio podcast using Amazon Bedrock for script generation and Amazon Polly for speech synthesis.
---

# Podcast Polly

Generate a two-voice conversational podcast from any content summary. The agent gathers and summarizes the source material; this skill handles script writing, audio synthesis via Amazon Polly, and mixing.

## When to Use

- User asks to create a podcast, audio summary, or audio briefing from any content
- User wants to turn a document, article, changelog, meeting notes, or research into audio
- User requests a "listen-friendly" version of written content
- User wants to regenerate audio from an existing script (different voices, music, etc.)
- User specifically requests Amazon Polly voices or AWS-native TTS

## Workflow

1. **Gather content** — Use your tools (web fetch, file read, API calls) to collect the source material the user wants turned into a podcast.
2. **Summarize** — Produce a plain-text content summary (1000–3000 words) structured with clear sections and bullet points. Include enough detail for an engaging conversation but not so much that it overwhelms the script generator.
3. **Invoke the skill** — Call `scripts/generate_podcast.py` with a subcommand and the appropriate options.

## Subcommands

The skill supports three subcommands for modular control over the pipeline:

### `generate` — Full pipeline

Runs the complete workflow: script generation, audio synthesis, and mixing. All artifacts are saved to a timestamped output folder.

```bash
python scripts/generate_podcast.py generate \
  --content-file <path_to_summary.txt> \
  --title "Episode Title" \
  --voice1 Matthew \
  --voice2 Danielle \
  --duration 2.0 \
  --intro-music assets/music.mp3 \
  --music-volume 60 \
  --polly-endpoint https://custom.endpoint.example.com
```

### `script` — Script generation only

Generates the podcast script without synthesizing audio. Useful for reviewing/editing the script before committing to synthesis.

```bash
python scripts/generate_podcast.py script \
  --content-file <path_to_summary.txt> \
  --title "Episode Title" \
  --duration 2.0
```

### `synthesize` — Audio from existing script

Synthesizes audio from an existing run directory's `script.json`. Allows re-generating audio with different voices, music, or settings without re-running script generation.

```bash
python scripts/generate_podcast.py synthesize \
  --run-dir output/20260712-1841_episode-title/ \
  --voice1 Ruth \
  --intro-music assets/new-music.mp3 \
  --music-volume 80
```

## Output Structure

All artifacts are saved to a timestamped folder under `output/`:

```
output/20260712-1841_episode-title/
├── config.json      # Full configuration used for the run
├── content.txt      # Content summary that was used
├── script.json      # Generated podcast script
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
| `--voice1` | No | `Matthew` | Lead presenter voice (name or Polly voice ID) |
| `--voice2` | No | `Danielle` | Co-presenter voice (name or Polly voice ID) |
| `--voice1-name` | No | *(inferred)* | Display name for voice 1 in dialogue |
| `--voice2-name` | No | *(inferred)* | Display name for voice 2 in dialogue |
| `--voice1-personality` | No | `assets/voice1_personality.txt` | Personality description for voice 1 (inline text or path to .txt file) |
| `--voice2-personality` | No | `assets/voice2_personality.txt` | Personality description for voice 2 (inline text or path to .txt file) |
| `--intro-speech` | No | `assets/intro_speech.txt` | Custom intro speech (inline text or path to .txt file). Supports `{title}`, `{voice1_name}`, `{voice2_name}` placeholders. Multi-line files produce one segment per line. |
| `--outro-speech` | No | `assets/outro_speech.txt` | Custom outro speech (inline text or path to .txt file) |
| `--duration` | No | `2.0` | Target duration in minutes |
| `--profile` | No | *(default)* | AWS profile for Bedrock |
| `--polly-profile` | No | *(same as profile)* | AWS profile for Polly |
| `--polly-endpoint` | No | *(none)* | Custom Polly endpoint URL (for beta/preview features) |
| `--intro-music` | No | *(none)* | Path to intro/outro music MP3 |
| `--music-volume` | No | `60` | Music volume percentage (1–100) |
| `--model` | No | *(default)* | Override the Bedrock model ID |
| `--thinking` | No | `false` | Enable adaptive thinking for script generation |
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
| `--polly-endpoint` | No | *(from config)* | Override Polly endpoint URL |
| `--intro-speech` | No | *(from config)* | Override intro speech |
| `--outro-speech` | No | *(from config)* | Override outro speech |

## Typical Agent Workflows

### Full generation (most common)

1. Gather and summarize content to a temp file
2. Run `generate` subcommand with all options
3. Clean up the temp content file
4. Report the output directory to the user

### Iterative workflow

1. Run `script` to generate and review the script
2. User reviews `script.json`, optionally edits it
3. Run `synthesize --run-dir <path>` to produce audio from the reviewed script

### Re-take with different settings

1. Run `synthesize --run-dir <existing-run> --voice1 Ruth --music-volume 80`
2. The new audio replaces `podcast.mp3` in the same run directory

## Content Summary Guidelines

When preparing the content summary for the skill, follow these guidelines for best results:

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

## Available Voices

Standard generative voices (always available):

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

Any raw Polly voice ID (e.g. `vc-56f8fbd479`) can also be passed directly.

## Prerequisites

- Python 3.10+
- ffmpeg on PATH
- AWS credentials with Bedrock (Claude) + Polly generative engine access
- For custom/beta endpoints: account must be allowlisted and endpoint URL known
- For Python 3.13+: install `audioop-lts` for pydub compatibility

## Error Handling

- If Bedrock returns an invalid script, the tool retries once with a simplified prompt
- If a Polly synthesis call fails, the error is reported with the specific segment number and voice ID
- Network/credential errors surface immediately with clear messages

## Notes

- The generative engine produces the most natural audio but requires allowlisting during beta
- Cloned voices (vc-* IDs) may require a custom endpoint URL via `--polly-endpoint`
- Target duration is approximate — actual length depends on speaking pace and number of turns
- The prompt template at `assets/prompt_template.txt` can be customized to change podcast style
- Host personalities are defined in `assets/voice1_personality.txt` and `assets/voice2_personality.txt` — edit these to change presenter behavior without touching the prompt template
- Personalities can also be overridden per-run via `--voice1-personality` and `--voice2-personality` (accepts inline text or a path to a .txt file)
- Intro and outro speech can be overridden per-run via `--intro-speech` and `--outro-speech` (accepts inline text or a path to a .txt file). The intro speech supports `{title}`, `{voice1_name}`, and `{voice2_name}` template variables.
- The default Bedrock model is `us.anthropic.claude-opus-4-6-v1`; use `--model` to override if this isn't available in your account
