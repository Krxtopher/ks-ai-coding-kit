# Narrator Kokoro — Reference

Detailed setup, configuration, and customization guide. The agent does not need this information during normal operation — consult it only when the user asks about setup, voices, or advanced CLI options.

## Prerequisites

1. Python 3.10+
2. An audio player: **afplay** (macOS built-in, used by default)
3. Python dependencies: `pip install -r <skill-path>/requirements.txt`

No API keys, cloud accounts, or network access required. All inference runs locally.

## Architecture

Kokoro uses a persistent daemon to avoid reloading the ONNX model on every utterance:

```
speak.py (client) ──Unix socket──▶ tts_daemon.py (background process)
                                        │
                                        ├─ Loads model once on first request
                                        ├─ Synthesizes speech to temp WAV
                                        └─ Plays via afplay (serialized)
```

- **First call:** The client auto-starts the daemon (~2–3s model load), then sends the message. Subsequent calls connect instantly.
- **Idle timeout:** The daemon self-terminates after 10 minutes of inactivity to avoid lingering processes.
- **Pre-emption:** Only one utterance plays at a time. Playback is serialized via a file lock — new requests queue behind the current one.

## CLI Options

```bash
# Speak a message (daemon auto-starts if needed)
python3 scripts/speak.py --message "Hello world"

# Override voice
python3 scripts/speak.py --message "Hello" --voice am_adam

# Override speed
python3 scripts/speak.py --message "Hello" --speed 1.2

# Stop the background daemon
python3 scripts/speak.py --stop-daemon

# Pipe text via stdin
echo "Hello world" | python3 scripts/speak.py
```

## Available Voices

| Voice ID | Gender | Style |
|----------|--------|-------|
| `bm_daniel` | Male | Warm, natural (default) |
| `af_sarah` | Female | Warm, conversational |
| `af_bella` | Female | Clear, friendly |
| `af_nicole` | Female | Smooth |
| `af_sky` | Female | Light, upbeat |
| `am_adam` | Male | Natural, casual |
| `am_echo` | Male | Calm |
| `am_eric` | Male | Deeper tone |

Voice IDs follow the pattern `{gender}{style}_{name}` where `a` = American, `b` = British, `f` = female, `m` = male.

## Bundled Model Files

The skill ships with these model files in `scripts/`:

| File | Size | Purpose |
|------|------|---------|
| `kokoro-v1.0.onnx` | ~80 MB | Speech synthesis model |
| `voices-v1.0.bin` | ~15 MB | Voice embeddings for all supported voices |

These are required for inference and cannot be removed.

## Daemon Management

The daemon stores its state in the system temp directory:

| File | Purpose |
|------|---------|
| `/tmp/kiro-tts-daemon-<UID>.sock` | Unix socket for client-daemon communication |
| `/tmp/kiro-tts-daemon-<UID>.pid` | PID file for process tracking |
| `/tmp/kiro-tts-narrator-<UID>.lock` | Playback serialization lock |

To manually stop the daemon:
```bash
python3 scripts/speak.py --stop-daemon
# or
python3 scripts/tts_daemon.py --stop
```

To run the daemon in foreground for debugging:
```bash
python3 scripts/tts_daemon.py
```

## Performance Notes

- **First utterance:** ~2–3 seconds (model load + synthesis + playback start)
- **Subsequent utterances:** ~800ms synthesis + playback
- **Memory usage:** ~200–400 MB while daemon is running (ONNX model in memory)
- **No network required:** Fully offline after installation

## Comparison with Cloud Narrators

| | narrator-kokoro | narrator-elevenlabs | narrator-polly |
|---|---|---|---|
| Network | None (offline) | Required | Required |
| API keys | None | ELEVENLABS_API_KEY | AWS credentials |
| Voice quality | Good | Excellent | Very good |
| Expressiveness | Basic prosody | Audio tags, emotional range | SSML, prosody control |
| Latency (first) | ~2–3s (model load) | ~500ms | ~500ms |
| Latency (subsequent) | ~800ms | ~300ms | ~300ms |
| Cost | Free | Per-character credits | Per-character AWS pricing |
| Model size | ~95 MB on disk | None (cloud) | None (cloud) |

Choose narrator-kokoro when you need fully offline narration, have no API keys available, or want zero ongoing cost.
