# Kiro Voice Response

Speaks agent responses aloud using Amazon Polly with the Gregory neural voice. Provides two hooks:

- **Prompt Acknowledgment** (`promptSubmit`) — Instantly plays a random short phrase ("One moment", "Hang on", etc.) when you send a message. Uses pre-generated MP3 files for near-zero latency (~100ms).
- **Response Recap** (`agentStop`) — After the agent finishes, generates a concise conversational summary of its response and speaks it aloud via Polly.

## How It Works

```
You send a message
  → promptSubmit hook fires
  → acknowledge.py picks a random MP3 from phrases/ and plays it (~100ms)

Agent finishes its response
  → agentStop hook fires
  → Agent generates a short spoken recap
  → speak.py calls Polly, queues the audio, plays via ffplay
```

Multiple audio clips are queued and played sequentially — they never overlap.

## Dependencies

### System

- **Python 3.10+**
- **ffplay** (part of FFmpeg) — used for audio playback

Install ffplay via Homebrew:

```bash
brew install ffmpeg
```

### Python

- **boto3** — AWS SDK for calling Polly

Install into a virtual environment:

```bash
pip install -r requirements.txt
```

### AWS

- An AWS account with **Amazon Polly** access
- The IAM role/user must have the `polly:SynthesizeSpeech` permission
- Credentials configured via standard AWS methods (`~/.aws/config`, environment variables, etc.)

Example minimal IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "polly:SynthesizeSpeech",
      "Resource": "*"
    }
  ]
}
```

## Installation

Copy the hook files to your workspace's `.kiro/hooks/` root and the supporting files into a subdirectory:

```bash
# From the ks-ai-coding-kit repo root:
cp hooks/kiro-voice-response/kiro-voice-response.kiro.hook /path/to/project/.kiro/hooks/
cp hooks/kiro-voice-response/kiro-voice-response-prompt.kiro.hook /path/to/project/.kiro/hooks/
cp -r hooks/kiro-voice-response /path/to/project/.kiro/hooks/kiro-voice-response
```

> [!IMPORTANT]
> Hook `.kiro.hook` files must be at the `.kiro/hooks/` root level — Kiro does not discover hooks inside subdirectories. The scripts and assets live in the subdirectory and are referenced by path from the hook files.

## File Structure

```
hooks/kiro-voice-response/
├── kiro-voice-response.kiro.hook          # agentStop — spoken recap
├── kiro-voice-response-prompt.kiro.hook   # promptSubmit — quick acknowledgment
├── acknowledge.py                          # Picks and plays a random phrase MP3
├── speak.py                                # Polly synthesis + queued playback
├── requirements.txt                        # Python dependencies (boto3)
├── phrases/                                # Pre-generated acknowledgment MP3s
│   ├── 02.mp3  (Give me a sec)
│   ├── 03.mp3  (One moment)
│   ├── 04.mp3  (Let me think)
│   ├── 07.mp3  (Bear with me)
│   ├── 09.mp3  (Mm-hmm)
│   ├── 10.mp3  (One sec)
│   ├── 11.mp3  (Hang on)
│   └── 12.mp3  (Alright, let's see)
└── README.md                               # This file
```

## Configuration

### Speech Rate

The `speak.py` script accepts a `--rate` flag to control speech speed:

```bash
python3 speak.py --rate 110% "Hello world"
```

Accepted values: percentages (`85%`, `110%`, `150%`) or keywords (`slow`, `medium`, `fast`, `x-fast`).

The agentStop hook prompt instructs the agent to pass `--rate 110%` by default.

### Voice

Change the voice with `--voice`:

```bash
python3 speak.py --voice Joanna "Hello world"
```

The default is `Gregory` (neural engine). Any Polly neural voice works.

### Adding/Removing Phrases

To regenerate or add phrases, use Polly directly:

```python
import boto3
polly = boto3.client("polly")
response = polly.synthesize_speech(
    Text='<speak><prosody rate="110%">Your phrase here</prosody></speak>',
    TextType="ssml",
    VoiceId="Gregory",
    Engine="neural",
    OutputFormat="mp3",
)
with open("phrases/13.mp3", "wb") as f:
    f.write(response["AudioStream"].read())
```

To remove a phrase, delete its MP3 file from the `phrases/` directory.

## Compatibility

Kiro IDE only.

## Platform Support

Currently macOS only (uses `ffplay` for audio playback). Linux support would work out of the box if `ffplay` is installed. Windows would require a different playback approach.
