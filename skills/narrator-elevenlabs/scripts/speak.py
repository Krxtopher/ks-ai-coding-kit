#!/usr/bin/env python3
"""
Text-to-speech narrator using ElevenLabs streaming API.

Streams audio from ElevenLabs and plays it back immediately via mpv or ffplay.
Designed for low-latency narration during coding sessions.

Usage:
    python speak.py --message "Hello world"
    python speak.py --message "Hello" --voice "JBFqnCBsd6RMkjVDRZzb"
    python speak.py --message "Hello" --speed 1.2
    python speak.py --message "Hello" --voice "abc123" --speed 1.1 --save
    echo "Hello world" | python speak.py

Environment:
    ELEVENLABS_API_KEY  — required. Your ElevenLabs API key.
    ELEVENLABS_VOICE_ID — optional. Default voice ID (overridden by config/--voice).
    ELEVENLABS_MODEL_ID — optional. Model to use (default: eleven_multilingual_v2).
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

# ─── Configuration ───────────────────────────────────────────────────────────

API_BASE = "https://api.elevenlabs.io/v1"

# Default voice: "George" — warm, conversational male voice
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_SPEED = 1.0
DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY = 0.75
DEFAULT_STYLE = 0.0

# Streaming latency optimization level (0-4).
# 2 = strong optimizations (~75% of max improvement, good quality tradeoff)
DEFAULT_LATENCY_OPT = 2

# Output format: mp3 at 44.1kHz/64kbps — good balance of quality and stream speed
OUTPUT_FORMAT = "mp3_44100_64"

# Config file lives alongside the skill (one level up from scripts/)
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR.parent / "config.json"

logger = logging.getLogger(__name__)


# ─── Config persistence ──────────────────────────────────────────────────────


def load_config() -> dict:
    """Load user preferences from config.json if it exists."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read config file: %s", e)
    return {}


def save_config(config: dict) -> None:
    """Write user preferences to config.json."""
    try:
        CONFIG_FILE.write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as e:
        print(f"Error: Could not save config: {e}", file=sys.stderr)


# ─── Audio playback ──────────────────────────────────────────────────────────


def find_player() -> list[str] | None:
    """Find a suitable audio player for streaming playback.

    Returns the command prefix as a list, or None if nothing found.
    Prefers mpv (lower latency) over ffplay.
    """
    if shutil.which("mpv"):
        return [
            "mpv",
            "--no-terminal",
            "--no-video",
            "--demuxer-max-bytes=128KiB",
            "--demuxer-readahead-secs=0.5",
            "-",
        ]
    if shutil.which("ffplay"):
        return [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel", "quiet",
            "-i", "pipe:0",
        ]
    return None


def _kill_previous_player() -> None:
    """Kill any previously-spawned narrator player process.

    Reads PID from a lockfile. Ensures only one narrator utterance plays at a
    time — new speech pre-empts the old.
    """
    pid_file = SCRIPT_DIR.parent / ".narrator.pid"
    if not pid_file.exists():
        return
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 15)  # SIGTERM
    except (ValueError, OSError):
        pass
    finally:
        try:
            pid_file.unlink()
        except OSError:
            pass


def _record_player_pid(pid: int) -> None:
    """Record the player PID so a subsequent invocation can kill it."""
    pid_file = SCRIPT_DIR.parent / ".narrator.pid"
    try:
        pid_file.write_text(str(pid))
    except OSError:
        pass


# ─── ElevenLabs streaming ───────────────────────────────────────────────────


def stream_speech(
    message: str,
    api_key: str,
    voice_id: str,
    model_id: str,
    speed: float,
    stability: float,
    similarity_boost: float,
    style: float,
    latency_opt: int,
    background: bool = False,
) -> None:
    """Stream TTS audio from ElevenLabs and pipe directly to audio player.

    If background=True, the script exits as soon as all audio data has been
    piped to the player process — playback continues in the background without
    blocking the caller.
    """
    player_cmd = find_player()
    if player_cmd is None:
        logger.error(
            "No audio player found. Install mpv (recommended) or ffplay."
        )
        print(
            "Error: No audio player found. Install mpv or ffplay.",
            file=sys.stderr,
        )
        return

    url = f"{API_BASE}/text-to-speech/{voice_id}/stream"
    params = {
        "output_format": OUTPUT_FORMAT,
        "optimize_streaming_latency": str(latency_opt),
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "text": message,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "speed": speed,
        },
    }

    # Start the audio player process, ready to receive piped audio
    player_proc = subprocess.Popen(
        player_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        with httpx.Client(timeout=30.0) as client:
            with client.stream("POST", url, params=params, headers=headers, json=body) as response:
                if response.status_code != 200:
                    error_body = response.read().decode("utf-8", errors="replace")
                    logger.error(
                        "ElevenLabs API error %d: %s",
                        response.status_code,
                        error_body,
                    )
                    print(
                        f"Error: ElevenLabs API returned {response.status_code}",
                        file=sys.stderr,
                    )
                    player_proc.stdin.close()
                    player_proc.wait()
                    return

                for chunk in response.iter_bytes(chunk_size=4096):
                    if chunk:
                        player_proc.stdin.write(chunk)
                        player_proc.stdin.flush()

    except httpx.TimeoutException:
        logger.error("Request to ElevenLabs timed out")
        print("Error: ElevenLabs request timed out", file=sys.stderr)
    except httpx.HTTPError as e:
        logger.error("HTTP error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
    except BrokenPipeError:
        # Player exited early — not critical
        pass
    finally:
        if player_proc.stdin and not player_proc.stdin.closed:
            player_proc.stdin.close()
        if not background:
            player_proc.wait()


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TTS narrator (ElevenLabs streaming)"
    )
    parser.add_argument("--message", "-m", help="Text to speak")
    parser.add_argument(
        "--voice",
        default=None,
        help="ElevenLabs voice ID (default: config > env > built-in)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"ElevenLabs model ID (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=None,
        help="Speech speed multiplier (default: 1.0)",
    )
    parser.add_argument(
        "--stability",
        type=float,
        default=None,
        help="Voice stability 0.0-1.0. Lower = more expressive, higher = more consistent (default: 0.5)",
    )
    parser.add_argument(
        "--similarity",
        type=float,
        default=None,
        help="Similarity boost 0.0-1.0. How closely to match the original voice (default: 0.75)",
    )
    parser.add_argument(
        "--style",
        type=float,
        default=None,
        help="Style exaggeration 0.0-1.0. Higher amplifies speaker style but adds latency (default: 0.0)",
    )
    parser.add_argument(
        "--latency",
        type=int,
        default=None,
        choices=[0, 1, 2, 3, 4],
        help=f"Streaming latency optimization 0-4 (default: {DEFAULT_LATENCY_OPT})",
    )
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Don't wait for playback to finish. Script exits after piping audio to player.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save current settings (voice, speed, stability, similarity, style, latency) to config.json",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print the current saved configuration and exit",
    )
    args = parser.parse_args()

    # ── Show config ──────────────────────────────────────────────────────
    if args.show_config:
        config = load_config()
        if config:
            print(json.dumps(config, indent=2))
        else:
            print("No config file found. Using defaults.")
        return

    # ── Load persisted preferences ───────────────────────────────────────
    config = load_config()

    # Resolution order: CLI flag > config.json > env var > built-in default
    voice_id = (
        args.voice
        or config.get("voice_id")
        or os.environ.get("ELEVENLABS_VOICE_ID")
        or DEFAULT_VOICE_ID
    )
    model_id = (
        args.model
        or config.get("model_id")
        or os.environ.get("ELEVENLABS_MODEL_ID")
        or DEFAULT_MODEL_ID
    )
    speed = args.speed if args.speed is not None else config.get("speed", DEFAULT_SPEED)
    stability = args.stability if args.stability is not None else config.get("stability", DEFAULT_STABILITY)
    similarity = args.similarity if args.similarity is not None else config.get("similarity_boost", DEFAULT_SIMILARITY)
    style = args.style if args.style is not None else config.get("style", DEFAULT_STYLE)
    latency = args.latency if args.latency is not None else config.get("latency", DEFAULT_LATENCY_OPT)

    # ── Save config if requested ─────────────────────────────────────────
    if args.save:
        new_config = {
            "voice_id": voice_id,
            "model_id": model_id,
            "speed": speed,
            "stability": stability,
            "similarity_boost": similarity,
            "style": style,
            "latency": latency,
        }
        save_config(new_config)
        print(f"Saved config to {CONFIG_FILE}")

    # ── Resolve API key ──────────────────────────────────────────────────
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        print(
            "Error: ELEVENLABS_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Get message ──────────────────────────────────────────────────────
    message = args.message
    if not message:
        if sys.stdin.isatty():
            # No message and no pipe — if --save was the intent, that's fine
            if args.save:
                return
            print("Error: provide --message or pipe text via stdin.", file=sys.stderr)
            sys.exit(1)
        message = sys.stdin.read().strip()

    if not message:
        return

    if args.background:
        # Fork the entire streaming + playback into a detached child process
        # so the script returns immediately to the caller.
        _kill_previous_player()  # Pre-empt any ongoing narration
        pid = os.fork()
        if pid > 0:
            # Parent — record child PID for pre-emption, then exit immediately
            _record_player_pid(pid)
            return
        # Child — detach from parent's process group
        os.setsid()
        # Redirect stdio to /dev/null so nothing ties us to the terminal
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
        stream_speech(
            message=message,
            api_key=api_key,
            voice_id=voice_id,
            model_id=model_id,
            speed=speed,
            stability=stability,
            similarity_boost=similarity,
            style=style,
            latency_opt=latency,
            background=False,  # child waits for player so audio completes
        )
        os._exit(0)
    else:
        _kill_previous_player()
        stream_speech(
            message=message,
            api_key=api_key,
            voice_id=voice_id,
            model_id=model_id,
            speed=speed,
            stability=stability,
            similarity_boost=similarity,
            style=style,
            latency_opt=latency,
            background=False,
        )


if __name__ == "__main__":
    main()
