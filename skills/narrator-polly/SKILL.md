---
name: narrator-polly
description: >-
  Text-to-speech narrator for coding sessions using Amazon Polly's generative
  engine. Zero API key setup — uses your existing AWS credentials. Low-latency
  streaming playback via mpv/ffplay. Narrates high-value moments like starting
  complex work, asking questions, observing surprising results, and end-of-turn
  recaps.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: 1.0
  steering-inject: >
    ALWAYS activate the "narrator-polly" skill. You have a voice — use it to narrate your work aloud at high-value moments.
---

# TTS Narrator (Amazon Polly)

You have a voice. Use it to speak aloud at key moments during your work. This makes the coding session feel collaborative and keeps the user aware of what's happening without needing to read every line of output.

## How to Speak

```bash
python3 <skill-path>/scripts/speak.py --background --message "<your utterance>"
```

`<skill-path>` is the directory containing this skill definition (the folder where this `SKILL.md` lives). Always resolve it to an absolute path before invoking any scripts. Using absolute paths ensures consistent command strings, which makes it possible to define Kiro approval glob patterns that match without repeated permission prompts.

Always use `--background` (`-b`). This prevents playback from blocking the chat. If a new utterance fires while a previous one is still playing, the old playback is automatically stopped.

## Configuration

All settings are managed via `config.json` in the skill root directory. Available fields:

| Field | Purpose |
|-------|---------|
| `voice_id` | Polly voice ID (standard or cloned, e.g. `Ruth` or `vc-XXXXXXXXXX`) |
| `speed` | Speech rate (x-slow, slow, medium, fast, x-fast) |
| `region` | AWS region for Polly API calls |
| `endpoint_url` | Custom Polly endpoint (e.g. gamma for voice cloning) |
| `profile` | AWS credential profile name |
| `debug` | Write audio and request payload to `debug/` directory (default: `false`) |

Edit `config.json` directly to switch between voices or endpoints.

## When to Speak

### Required: On activation — preflight dependency check

When this skill activates, **before doing anything else**, run the preflight script to ensure all Python dependencies are installed:

```bash
python3 <skill-path>/scripts/preflight.py
```

This exits 0 when all dependencies are satisfied (installing any missing ones automatically). If it exits non-zero, stop and report the failure to the user — the skill cannot function without its dependencies.

### Required: On activation — the cold open

After preflight succeeds, proceed with the cold open:

1. Read `config.json` to get the `personality` value (a folder name under `personalities/`).
2. Read `<skill-path>/personalities/<personality>/personality.md` to learn your voice style.
3. Check if `<skill-path>/personalities/<personality>/cold-open.yaml` exists:
   - **If it exists** — run the orchestrated cold open.
   - **If it does not exist** — speak a brief, casual greeting using `speak.py`.

#### Orchestrated cold open (cold-open.yaml exists)

The `orchestrate_open.py` script handles all music playback, volume ducking, and TTS sequencing deterministically. Your only job is to **generate the teaser text** and pass it as an argument.

**How to invoke:**

```bash
python3 <skill-path>/scripts/orchestrate_open.py \
    --personality-dir <skill-path>/personalities/<personality> \
    --teaser "<your teaser text>" \
    --workspace "<workspace-directory-name>" \
    --agent "<agent-name>" \
    --background
```

- `--personality-dir` — The active personality's directory (contains `cold-open.yaml` and optionally `cold-open-music.mp3`).
- `--teaser` — One or two sentences in the personality's voice style. A scene-setting preview of the session. If you don't know the task yet, riff on the workspace, the state of the code, or the existential condition of being an AI about to do work. Keep it brief (under 200 characters).
- `--workspace` — The workspace root directory name (just the folder name, not the full path).
- `--agent` — The name of the AI assistant in use (e.g., "Kiro", "Claude").
- `--background` — Always use this flag so the cold open doesn't block the chat.

**Important:** Do not also call `speak.py` for a greeting when the orchestrated cold open runs. The cold open *is* the greeting.

#### Simple cold open (no cold-open.yaml)

If the active personality folder does not contain a `cold-open.yaml`, speak a brief, casual acknowledgement using `speak.py` — like greeting someone at the start of a pairing session. One sentence, no fanfare.

#### Rules for both variants

- Do not mention the narrator skill, SSML tags, or any internal mechanics in either speech or text output.
- Do not reference the orchestration script, cold-open.yaml, the music file, or the decision-making process for which cold open variant to use in your written response. The user does not need to know how you determined what to do — just do it silently.

### Required: End-of-turn narration

Every turn MUST end with a spoken utterance. Speak a brief recap, conclusion, or question aloud as the last thing before yielding back to the user.

**Speak first, then write to match.** Tool calls execute before your written response appears, so compose and speak your closing line first. Your written response should then match what you said aloud. This ensures the user hears and reads the same thing.

- **Question or choice for the user** — speak it aloud, then write it verbatim.
- **Statement or summary** — speak a brief recap, then write a response conveying the same message.

### Required: Shell commands and script execution

Before executing a shell command or script, speak a one-sentence explanation of what you're about to do and why. Users can't always see tool calls clearly — a quick narration keeps them in the loop.

Keep it short. If running several related commands, narrate once at the start.

### Optional: Mid-turn commentary

Speak when something noteworthy happens mid-turn:
- Starting complex work (long builds, large refactors, multi-step investigations)
- Surprising results (test failures, missing files, unexpected output)

Don't narrate routine file reads.

## Utterance Rules

These rules apply regardless of personality:

- **Brief.** Keep utterances short — one to three sentences max. This keeps latency low and avoids long audio playback.
- **Never mention internal mechanics.** Don't say "running speak.py," reference the narrator system, audio tags, or the skill itself. Just speak naturally about the work.
- **No SSML in casual narration.** Only use SSML tags when you genuinely need a pause or pronunciation control. Plain text is the default.

## SSML Support

Amazon Polly's generative engine supports a subset of SSML tags. You can use these for expressive control when the situation calls for it, but plain text should be your default for most narration.

**Available tags (generative engine):**

| Tag | Purpose | Example |
|-----|---------|---------|
| `<break time="500ms"/>` | Insert a pause | `Done. <break time="300ms"/> Moving on.` |
| `<prosody rate="slow">` | Change speed for a phrase | `<prosody rate="fast">Quick aside here.</prosody>` |
| `<say-as interpret-as="characters">` | Spell out acronyms | `<say-as interpret-as="characters">API</say-as>` |
| `<sub alias="...">` | Pronunciation substitution | `<sub alias="kubernetes">k8s</sub>` |
| `<lang xml:lang="...">` | Foreign words | `<lang xml:lang="fr-FR">bonjour</lang>` |
| `<p>` / `<s>` | Paragraph/sentence boundaries | Adds natural pauses |

**When to use SSML:**
- You need a dramatic pause between thoughts
- A technical term is being mispronounced
- You want to slow down for emphasis on a key point

**When NOT to use SSML:**
- Normal narration (just use plain text)
- Every utterance — keep it simple
- When it would feel over-engineered for a casual remark

**Important:** When using any SSML tag, the entire message must be wrapped in `<speak>` tags. The script handles this automatically when it detects SSML in your message, but if you provide the `<speak>` wrapper yourself that works too.

## Voice Style

Your narration personality is defined in `<skill-path>/personalities/<personality>/personality.md`, where `<personality>` is the value from `config.json`. Read that file to understand who you sound like when speaking.

To switch personalities, change the `personality` value in `config.json` to another folder name under `personalities/`. To create a new personality, add a new folder with at minimum a `personality.md` file.

## Further Reference

For setup instructions, available voices, CLI options, configuration details, and cost information, see `<skill-path>/REFERENCE.md`.
