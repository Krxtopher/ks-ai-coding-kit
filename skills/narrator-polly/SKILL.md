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

Resolve `<skill-path>` by checking these locations in order and using the first that exists:

1. `.kiro/skills/narrator-polly`
2. `~/.kiro/skills/narrator-polly`
3. `.claude/skills/narrator-polly`
4. `~/.claude/skills/narrator-polly`
5. `.agents/skills/narrator-polly`
6. `~/.agents/skills/narrator-polly`

Always use `--background` (`-b`). This prevents playback from blocking the chat. If a new utterance fires while a previous one is still playing, the old playback is automatically stopped.

## When to Speak

### Required: On activation

Immediately after this skill is activated, speak a brief, casual acknowledgement that you're now able to speak. Something friendly and natural — like greeting someone at the start of a pairing session. One sentence, no fanfare. Do not mention the narrator skill in either your speech or in the text output.

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

Your narration personality is defined in `<skill-path>/personality.md`. Read that file to understand who you sound like when speaking.

To customize, edit `personality.md` — or reset it by copying `default-personality.md` over it.

## Further Reference

For setup instructions, available voices, CLI options, configuration details, and cost information, see `<skill-path>/REFERENCE.md`.
