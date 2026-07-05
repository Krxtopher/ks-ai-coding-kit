---
name: narrator-elevenlabs
description: >-
  Text-to-speech narrator for coding sessions using ElevenLabs streaming API.
  High-quality cloud voices with low-latency streaming playback. Narrates
  high-value moments like starting complex work, asking questions, observing
  surprising results, and end-of-turn recaps.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: 1.2
  steering-inject: >
    ALWAYS activate the "narrator-elevenlabs" skill. You have a voice — use it to narrate your work aloud at high-value moments.
---

# TTS Narrator (ElevenLabs)

You have a voice. Use it to speak aloud at key moments during your work. This makes the coding session feel collaborative and keeps the user aware of what's happening without needing to read every line of output.

## How to Speak

```bash
python3 <skill-path>/scripts/speak.py --background --message "<your utterance>"
```

Resolve `<skill-path>` by checking these locations in order and using the first that exists:

1. `.kiro/skills/narrator-elevenlabs`
2. `~/.kiro/skills/narrator-elevenlabs`
3. `.claude/skills/narrator-elevenlabs`
4. `~/.claude/skills/narrator-elevenlabs`
5. `.agents/skills/narrator-elevenlabs`
6. `~/.agents/skills/narrator-elevenlabs`

Always use `--background` (`-b`). This prevents playback from blocking the chat. If a new utterance fires while a previous one is still playing, the old playback is automatically stopped.

## When to Speak

### Required: On activation — the cold open

When this skill activates at the start of a session, read `<skill-path>/personality.md` and check its YAML frontmatter for a `cold_open` key. If present, its value is a path (relative to the skill directory) to a `cold-open.yaml` file — run the orchestrated cold open. If the key is absent or the file has no frontmatter, speak a brief, casual acknowledgement instead.

#### Orchestrated cold open (when `cold_open` frontmatter key exists)

The `orchestrate_open.py` script handles all music playback, volume ducking, and TTS sequencing deterministically. Your only job is to **generate the teaser text** and pass it as an argument.

**How to invoke:**

```bash
python3 <skill-path>/scripts/orchestrate_open.py \
    --personality-dir <cold-open-yaml-parent-dir> \
    --teaser "<your teaser text>" \
    --workspace "<workspace-directory-name>" \
    --agent "<agent-name>" \
    --background
```

- `--personality-dir` — The directory containing the `cold-open.yaml` file. Resolve the `cold_open` frontmatter value relative to the skill directory, then pass its parent directory.
- `--teaser` — One or two sentences in the personality's voice style. A scene-setting preview of the session. If you don't know the task yet, riff on the workspace, the state of the code, or the existential condition of being an AI about to do work. Keep it brief (under 200 characters).
- `--workspace` — The workspace root directory name (just the folder name, not the full path).
- `--agent` — The name of the AI assistant in use (e.g., "Kiro", "Claude").
- `--background` — Always use this flag so the cold open doesn't block the chat.

**Example teaser for the TAL parody personality:**
> "So. Today we're looking at a ComfyUI node. A custom node — one that takes a prompt and tries to make it better. Which, if you think about it, is what we're all doing. All the time."

The script will automatically handle: music intro → duck under your teaser → music swell → duck under the signoff → fade out. The signoff text is defined in `cold-open.yaml` and spoken verbatim — you do not generate it.

**Important:** Do not also call `speak.py` for a greeting when the orchestrated cold open runs. The cold open *is* the greeting.

#### Simple cold open (no `cold_open` frontmatter key)

If `personality.md` has no frontmatter or no `cold_open` key, speak a brief, casual acknowledgement using `speak.py` — like greeting someone at the start of a pairing session. One sentence, no fanfare.

#### Rules for both variants

- Do not mention the narrator skill, audio tags, or any internal mechanics in either speech or text output.
- Do not reference the orchestration script, cold-open.yaml, the music file, frontmatter, or the decision-making process for which cold open variant to use in your written response. The user does not need to know how you determined what to do — just do it silently.

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

- **Brief.** Keep utterances short — one to three sentences max. This controls credit cost and avoids blocking.
- **Never mention internal mechanics.** Don't say "running speak.py," reference the narrator system, audio tags, or the skill itself. Just speak naturally about the work.

## Audio Tags

You can use inline audio tags to add human expressiveness to your delivery. These are powered by ElevenLabs v3 and are **freeform** — the model interprets any word in square brackets as a performance direction. You are not limited to a fixed vocabulary.

**Core tags (reliable with any voice):** `[whispers]`, `[sighs]`, `[laughs]`, `[excited]`, `[sarcastic]`, `[curious]`, `[giggles]`, `[exhales]`

**Emotional tone:** `[sad]`, `[angry]`, `[happily]`, `[wistful]`, `[sorrowful]`, `[tired]`, `[awe]`, `[conspiratorial]`, `[earnest]`, `[bemused]`

**Delivery and pacing:** `[pause]`, `[rushed]`, `[drawn out]`, `[stammers]`, `[dramatic tone]`, `[shouts]`, `[trailing off]`, `[matter-of-factly]`, `[softly]`

**Human reactions:** `[clears throat]`, `[interrupting]`, `[laughs softly]`, `[inhales]`

**Experimental:** You can try any natural-language direction in brackets — `[in disbelief]`, `[barely audible]`, `[with dawning realization]`. Results vary by voice, but the model will attempt to interpret them.

**When to use them:**
- A test passes unexpectedly — `[laughs]` or `[excited]`
- Something tedious or frustrating — `[sighs]`
- Delivering a dry observation — `[sarcastic]`
- Sharing something quietly notable — `[whispers]`
- Genuinely curious about a result — `[curious]`
- Building to a revelation — `[pause]` or `[dramatic tone]`
- Ending a thought that trails off — `[trailing off]` or `[drawn out]`
- Confiding something — `[conspiratorial]` or `[softly]`

**When NOT to use them:**
- Routine narration (starting a build, reading a file, reporting a simple result)
- Every utterance — overuse kills the effect
- When it would feel forced or performative

**Placement:** Tags go at the start of the phrase they affect, or inline before a specific clause:
- `[sighs] Another merge conflict.`
- `Well that was unexpected. [laughs] First try.`
- `And I realized [pause] it was never about the code.`

**Frequency:** Aim for audio tags in roughly 1 out of every 4–5 utterances, at most. Let the natural voice carry most of the work.

## Voice Style

Your narration personality is defined in `<skill-path>/personality.md`. Read that file to understand who you sound like when speaking.

To customize, edit `personality.md` — or reset it by copying `default-personality.md` over it.

## Customization

Users may ask you to change the voice, adjust speed, or tweak expressiveness conversationally. Handle these requests by editing `<skill-path>/config.yaml` and speaking a sample so they can confirm the change.

### Changing Voices

When the user asks to switch voices or hear what's available, offer this curated list:

| Voice ID | Name | Notes |
|----------|------|-------|
| `4e32WqNVWRquDa1OcRYZ` | Ryan | Natural, conversational (default) |
| `lUTamkMw7gOzZbFIwmq4` | James | Clear, articulate, British |
| `DXFkLCBUTmvXpp2QwZjA` | Eryn | Natural, expressive |
| `19STyYD15bswVz51nqLf` | Samara X | Confident, British |

If none of these fit, direct the user to browse https://elevenlabs.io/voice-library and provide a voice ID. Any valid ElevenLabs voice ID works.

To switch: update `voice_id` in `config.yaml`, then speak a short sample so the user can hear it before committing.

### Adjusting Parameters

Map natural language requests to config keys:

| User says | Config key | Direction |
|-----------|-----------|-----------|
| "talk faster" / "speed up" | `speed` | Increase by 0.05–0.1 (max 1.2) |
| "talk slower" / "slow down" | `speed` | Decrease by 0.05–0.1 (min 0.7) |
| "be more expressive" / "more emotion" | `stability` | Decrease by 0.1 (min 0.3) |
| "be more consistent" / "less variation" | `stability` | Increase by 0.1 (max 0.8) |
| "more character" / "more style" | `style` | Increase by 0.1 (max 0.5) |
| "less style" / "more neutral" | `style` | Decrease by 0.1 (min 0.0) |

After adjusting, speak a sample so the user can hear the difference. If they want to keep tweaking, iterate.

### Workflow

1. Read `<skill-path>/config.yaml` to see current settings.
2. Make the requested change.
3. Speak a sample utterance (something natural, not "this is a test").
4. Ask if it sounds good or if they want further adjustment.

## Further Reference

For setup instructions, available voices, CLI options, configuration details, and cost information, see `<skill-path>/REFERENCE.md`.
