#!/usr/bin/env python3
"""
Text-to-speech narrator using Amazon Polly (generative engine).

Streams audio from Amazon Polly's SynthesizeSpeech API and plays it back
immediately via mpv or ffplay. Designed for low-latency narration during
coding sessions.

Usage:
    python speak.py --message "Hello world"
    python speak.py --message "Hello" --voice "Matthew"
    python speak.py --message "Hello" --speed fast
    python speak.py --message "Hello" --voice "Ruth" --save
    echo "Hello world" | python speak.py

Configuration is managed entirely via config.json in the skill root directory.
CLI flags override config.json values when provided.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

# ─── Configuration ───────────────────────────────────────────────────────────

ENGINE = "generative"

# Default voice: "Ruth" — warm, natural US female generative voice
DEFAULT_VOICE_ID = "Ruth"
DEFAULT_SPEED = "medium"  # prosody rate: x-slow, slow, medium, fast, x-fast
DEFAULT_REGION = "us-west-2"

# Output format: MP3 at 24kHz — universally supported, good quality
OUTPUT_FORMAT = "mp3"
SAMPLE_RATE = "24000"

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
            "--demuxer-max-bytes=512KiB",
            "--audio-buffer=1",
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


# ─── SSML wrapping ───────────────────────────────────────────────────────────


def wrap_ssml(text: str, speed: str) -> tuple[str, str]:
    """Wrap text in SSML if speed is non-default or text contains SSML tags.

    Returns (text_or_ssml, text_type) where text_type is 'ssml' or 'text'.
    """
    has_ssml = "<" in text and ">" in text
    needs_prosody = speed != "medium"

    if not has_ssml and not needs_prosody:
        return text, "text"

    # If user already provided <speak> wrapper, strip it so we can re-wrap
    inner = text
    if inner.strip().startswith("<speak>") and inner.strip().endswith("</speak>"):
        inner = inner.strip()[7:-8]

    if needs_prosody:
        inner = f'<prosody rate="{speed}">{inner}</prosody>'

    return f"<speak>{inner}</speak>", "ssml"


# ─── Amazon Polly streaming ─────────────────────────────────────────────────


def _write_debug_artifacts(
    request_params: dict,
    audio_data: bytes,
    voice_id: str,
) -> None:
    """Write audio file and request payload JSON to the debug/ directory."""
    debug_dir = SCRIPT_DIR.parent / "debug"
    debug_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_name = f"{timestamp}_{voice_id}"

    audio_path = debug_dir / f"{base_name}.mp3"
    payload_path = debug_dir / f"{base_name}.json"

    try:
        audio_path.write_bytes(audio_data)
        payload_path.write_text(
            json.dumps(request_params, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("Could not write debug artifacts: %s", e)


def stream_speech(
    message: str,
    voice_id: str,
    speed: str,
    region: str,
    endpoint_url: str | None = None,
    profile: str | None = None,
    debug: bool = False,
) -> None:
    """Stream TTS audio from Amazon Polly and pipe directly to audio player."""
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

    # Prepare the text (wrap in SSML if needed)
    text_content, text_type = wrap_ssml(message, speed)

    # Create Polly client with connection pooling optimized for low latency
    boto_config = BotoConfig(
        region_name=region,
        retries={"max_attempts": 2, "mode": "adaptive"},
    )
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client_kwargs: dict = {"config": boto_config}
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url
    polly = session.client("polly", **client_kwargs)

    # Build the request parameters
    request_params = {
        "Engine": ENGINE,
        "OutputFormat": OUTPUT_FORMAT,
        "SampleRate": SAMPLE_RATE,
        "Text": text_content,
        "TextType": text_type,
        "VoiceId": voice_id,
    }

    try:
        response = polly.synthesize_speech(**request_params)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        logger.error("Polly API error %s: %s", error_code, error_msg)
        print(f"Error: Polly returned {error_code}: {error_msg}", file=sys.stderr)
        return
    except BotoCoreError as e:
        logger.error("AWS SDK error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return

    # The AudioStream is a streaming body — read chunks and pipe to player
    audio_stream = response["AudioStream"]

    # Start the audio player process, ready to receive piped audio
    player_proc = subprocess.Popen(
        player_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    debug_chunks: list[bytes] = [] if debug else []

    try:
        for chunk in audio_stream.iter_chunks(chunk_size=4096):
            if chunk:
                player_proc.stdin.write(chunk)
                player_proc.stdin.flush()
                if debug:
                    debug_chunks.append(chunk)
    except BrokenPipeError:
        # Player exited early — not critical
        pass
    except Exception as e:
        logger.error("Error streaming audio: %s", e)
        print(f"Error: {e}", file=sys.stderr)
    finally:
        if player_proc.stdin and not player_proc.stdin.closed:
            player_proc.stdin.close()
        player_proc.wait()
        audio_stream.close()

    # Write debug artifacts after playback completes
    if debug and debug_chunks:
        _write_debug_artifacts(request_params, b"".join(debug_chunks), voice_id)


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TTS narrator (Amazon Polly generative engine)"
    )
    parser.add_argument("--message", "-m", help="Text to speak")
    parser.add_argument(
        "--voice",
        default=None,
        help="Polly voice ID, e.g. Ruth, Matthew, Stephen (default: env > config > Ruth)",
    )
    parser.add_argument(
        "--speed",
        default=None,
        choices=["x-slow", "slow", "medium", "fast", "x-fast"],
        help="Speech speed (default: medium)",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region for Polly (default: config > AWS_DEFAULT_REGION > us-west-2)",
    )
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Don't wait for playback to finish. Script exits after piping audio to player.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save current settings (voice, speed, region) to config.json",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print the current saved configuration and exit",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Write audio file and request payload to debug/ directory for inspection",
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

    # Resolution order: CLI flag > config.json > built-in default
    voice_id = args.voice or config.get("voice_id", DEFAULT_VOICE_ID)
    speed = args.speed or config.get("speed", DEFAULT_SPEED)
    region = args.region or config.get("region", DEFAULT_REGION)
    endpoint_url = config.get("endpoint_url")
    profile = config.get("profile")
    debug = args.debug or config.get("debug", False)

    # ── Save config if requested ─────────────────────────────────────────
    if args.save:
        new_config: dict = {
            "voice_id": voice_id,
            "speed": speed,
            "region": region,
        }
        if endpoint_url:
            new_config["endpoint_url"] = endpoint_url
        if profile:
            new_config["profile"] = profile
        save_config(new_config)
        print(f"Saved config to {CONFIG_FILE}")

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
            voice_id=voice_id,
            speed=speed,
            region=region,
            endpoint_url=endpoint_url,
            profile=profile,
            debug=debug,
        )
        os._exit(0)
    else:
        _kill_previous_player()
        stream_speech(
            message=message,
            voice_id=voice_id,
            speed=speed,
            region=region,
            endpoint_url=endpoint_url,
            profile=profile,
            debug=debug,
        )


if __name__ == "__main__":
    main()
