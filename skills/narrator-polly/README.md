# Narrator Polly

A text-to-speech skill that gives your AI coding assistant a voice using Amazon Polly's generative engine. It streams synthesized speech and plays it back in real-time through your system's audio player (mpv or ffplay).

The skill works with any AI coding tool that supports agent skills — Kiro, Claude Code, Cursor, Codex, etc.

## Quick Start

1. Install an audio player: `brew install mpv`
2. Ensure your AWS credentials are configured (`aws sts get-caller-identity` should succeed)
3. Install the Python dependency: `pip install boto3`
4. Activate the skill in your AI coding tool

That's it. The assistant will start narrating its work aloud.

## Configuration

All settings live in `config.json` at the skill root directory. This is the single source of truth — no environment variables are needed.

```json
{
  "voice_id": "Ruth",
  "speed": "medium",
  "region": "us-west-2",
  "endpoint_url": null,
  "profile": null
}
```

| Field | Purpose | Default |
|-------|---------|---------|
| `voice_id` | Polly voice ID (standard or cloned) | `Ruth` |
| `speed` | Speech rate: x-slow, slow, medium, fast, x-fast | `medium` |
| `region` | AWS region for Polly calls | `us-west-2` |
| `endpoint_url` | Custom Polly endpoint (e.g. gamma for voice cloning) | Standard endpoint |
| `profile` | AWS credential profile name | Default profile |

Edit the file directly, or ask your coding agent to change it — it knows how to update the config.

### Example: Standard Voice

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
  "voice_id": "vc-56f8fbd479",
  "speed": "medium",
  "region": "us-east-1",
  "endpoint_url": "https://gamma.us-east-1.parrot.a2z.com/",
  "profile": "polly-shared"
}
```

## Resolution Order

Each setting is resolved in this order (first match wins):

1. CLI flag (e.g. `--voice`, `--region`)
2. `config.json` in the skill directory
3. Built-in default

## Available Voices

The skill uses Polly's generative engine, which produces the most natural-sounding speech. Popular English voices:

| Voice | Gender | Accent | Notes |
|-------|--------|--------|-------|
| Ruth | Female | US | Calm, composed (default) |
| Matthew | Male | US | Warm, conversational |
| Stephen | Male | US | Clear, professional |
| Danielle | Female | US | Natural, friendly |
| Amy | Female | UK | British, clear |
| Brian | Male | UK | British, authoritative |

Full list: https://docs.aws.amazon.com/polly/latest/dg/generative-voices.html

## Customization

- **Change the personality/tone:** Edit `personality.md` in the skill directory
- **Reset personality:** Copy `default-personality.md` over `personality.md`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No audio plays | Install mpv (`brew install mpv`) or ffplay |
| `ExpiredTokenException` | Refresh your AWS credentials for the profile |
| `ResourceNotFoundException` for a cloned voice | Cloned voices are account-scoped — use the profile for the account that created the voice |
| `ThrottlingException` | Wait a moment and retry; generative engine has lower TPS limits than standard |
| Silent output (0 bytes) | Try a different voice or region — see the [known issues](#known-issues) section |

## Known Issues

- The **Matthew** generative voice may return empty audio streams or persistent throttling on some accounts (as of July 2026). Ruth and other voices are unaffected. Use Ruth as the default.

## Cost

Generative engine: ~$30 per million characters. A typical coding session with 20–40 short utterances costs roughly $0.06–$0.12.
