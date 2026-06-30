#!/usr/bin/env python3
"""
Text-to-speech narrator using Amazon Bedrock (Nova Micro) + Amazon Polly.

Usage:
    echo '{"trigger":"preToolUse","toolInput":{"command":"npm run build"}}' | python speak.py --context
    python speak.py --message "Hello world"

In --context mode, reads JSON hook context from stdin, asks a fast LLM
to generate a short spoken utterance, then synthesizes and plays it.
"""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

import boto3

# ─── Configuration ───────────────────────────────────────────────────────────

# LLM for utterance generation
MODEL_ID = "us.amazon.nova-micro-v1:0"  # Swap to "us.amazon.nova-lite-v2:0" for higher quality

# Polly voice
VOICE_ID = "Ruth"
ENGINE = "generative"
OUTPUT_FORMAT = "mp3"

# AWS region (used for both Bedrock and Polly)
REGION = "us-east-1"

# Playback lock file — serializes audio so utterances don't overlap
LOCK_FILE = os.path.join(tempfile.gettempdir(), "kiro-tts-narrator.lock")

# Voice personality prompt — loaded from file next to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PERSONALITY_FILE = SCRIPT_DIR / "voice-personality.md"


def load_personality() -> str:
    """Load the voice personality prompt from the companion text file."""
    try:
        return PERSONALITY_FILE.read_text().strip()
    except FileNotFoundError:
        # Fallback if personality file is missing
        return (
            "You are a casual AI coding assistant named Kiro. "
            "Given a JSON event, produce a short first-person spoken sentence (max 20 words). "
            "Output ONLY the sentence, or SKIP if nothing noteworthy happened."
        )


def generate_utterance(context: dict) -> str:
    """Ask Bedrock Nova Micro to generate a short spoken message from hook context.

    Returns an empty string if the LLM decides there's nothing worth saying (SKIP).
    """
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)

    system_prompt = load_personality()
    user_message = json.dumps(context, default=str)

    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
        inferenceConfig={
            "maxTokens": 50,
            "temperature": 0.7,
        },
    )

    output = response["output"]["message"]["content"][0]["text"]
    output = output.strip().strip('"')

    # LLM signals nothing noteworthy happened
    if output.upper() == "SKIP":
        return ""

    return output


def synthesize_and_play(message: str) -> None:
    """Call Polly to synthesize speech, then fork a background child to play it.

    The parent process returns immediately (unblocking the hook), while the
    child acquires an exclusive file lock and plays audio. If another child
    is already playing, the new child waits its turn — serializing playback
    without blocking the agent.
    """
    if not message.strip():
        return

    polly = boto3.client("polly", region_name=REGION)

    response = polly.synthesize_speech(
        Text=message,
        OutputFormat=OUTPUT_FORMAT,
        VoiceId=VOICE_ID,
        Engine=ENGINE,
    )

    with tempfile.NamedTemporaryFile(suffix=f".{OUTPUT_FORMAT}", delete=False) as tmp:
        tmp.write(response["AudioStream"].read())
        tmp_path = tmp.name

    # Fork: parent returns immediately, child handles queued playback
    pid = os.fork()
    if pid != 0:
        # Parent — return without waiting
        return

    # ─── Child process ───────────────────────────────────────────────────
    # Detach from parent's process group so we don't get killed with it
    os.setsid()

    # Acquire exclusive lock (blocks until previous playback finishes)
    lock_fd = open(LOCK_FILE, "w")
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        subprocess.run(
            ["afplay", tmp_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Exit child cleanly without running atexit handlers
    os._exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Polly TTS narrator for Kiro hooks")
    parser.add_argument("--message", "-m", help="Speak this message directly (skip LLM)")
    parser.add_argument(
        "--context",
        action="store_true",
        help="Read JSON context from stdin, generate utterance via LLM, then speak",
    )
    args = parser.parse_args()

    if args.message:
        synthesize_and_play(args.message)
    elif args.context:
        raw = sys.stdin.read()
        try:
            context = json.loads(raw)
        except json.JSONDecodeError:
            context = {}

        # Skip self-referential invocations (e.g. pre-shell firing for speak.py itself)
        tool_input = context.get("toolInput", {})
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
        if "speak.py" in command:
            return

        message = generate_utterance(context)
        synthesize_and_play(message)
    else:
        # Plain text from stdin — speak directly
        message = sys.stdin.read().strip()
        synthesize_and_play(message)


if __name__ == "__main__":
    main()
