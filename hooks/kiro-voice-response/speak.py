#!/usr/bin/env python3
"""Synthesize speech from text using Amazon Polly and play it back with queuing."""

import argparse
import fcntl
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import boto3

QUEUE_DIR = Path(tempfile.gettempdir()) / "kiro-voice-queue"
LOCK_FILE = QUEUE_DIR / ".player.lock"

# Player script that processes queued audio files sequentially.
PLAYER_SCRIPT = '''
import fcntl, os, sys, time, subprocess
from pathlib import Path

queue_dir = Path(sys.argv[1])
lock_file = queue_dir / ".player.lock"

lock_fd = open(lock_file, "w")
try:
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(0)

try:
    while True:
        files = sorted(queue_dir.glob("*.mp3"))
        if not files:
            time.sleep(0.3)
            files = sorted(queue_dir.glob("*.mp3"))
            if not files:
                break
        for f in files:
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(f)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            f.unlink(missing_ok=True)
finally:
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()
    lock_file.unlink(missing_ok=True)
'''


def synthesize_and_queue(text: str, voice_id: str = "Gregory", engine: str = "neural", rate: str = "100%") -> None:
    """Send text to Amazon Polly and queue the audio for sequential playback."""
    polly = boto3.client("polly")

    # Truncate to Polly's 3000-character limit for neural voices
    if len(text) > 3000:
        text = text[:2997] + "..."

    # Wrap in SSML with prosody if rate is not default
    if rate != "100%":
        ssml_text = f'<speak><prosody rate="{rate}">{text}</prosody></speak>'
        text_type = "ssml"
    else:
        ssml_text = text
        text_type = "text"

    response = polly.synthesize_speech(
        Text=ssml_text,
        TextType=text_type,
        VoiceId=voice_id,
        Engine=engine,
        OutputFormat="mp3",
    )

    # Ensure queue directory exists
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # Write audio to a sequentially-named file in the queue directory.
    filename = f"{time.time_ns():020d}_{os.getpid()}.mp3"
    audio_path = QUEUE_DIR / filename
    audio_path.write_bytes(response["AudioStream"].read())

    # Launch the player process (it no-ops if one is already running).
    subprocess.Popen(
        [sys.executable, "-c", PLAYER_SCRIPT, str(QUEUE_DIR)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Speak text using Amazon Polly.")
    parser.add_argument("text", nargs="?", help="Text to speak. Reads from stdin if omitted.")
    parser.add_argument("--voice", default="Gregory", help="Polly voice ID (default: Gregory)")
    parser.add_argument("--engine", default="neural", help="Polly engine (default: neural)")
    parser.add_argument("--rate", default="100%", help="Speech rate as percentage or keyword (default: 100%%)")
    args = parser.parse_args()

    text = args.text if args.text else sys.stdin.read().strip()
    if not text:
        print("Error: No text provided.", file=sys.stderr)
        sys.exit(1)

    synthesize_and_queue(text, voice_id=args.voice, engine=args.engine, rate=args.rate)


if __name__ == "__main__":
    main()
