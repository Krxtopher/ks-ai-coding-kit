#!/usr/bin/env python3
"""
Text-to-speech narrator client — sends messages to the TTS daemon.

Usage:
    python speak.py --message "Hello world"

If the daemon isn't running, this script auto-starts it in the background
and waits for it to become ready before sending the message.
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
DAEMON_SCRIPT = SCRIPT_DIR / "tts_daemon.py"
SOCKET_PATH = Path(tempfile.gettempdir()) / "kiro-tts-daemon.sock"
PID_FILE = Path(tempfile.gettempdir()) / "kiro-tts-daemon.pid"

# Default voice settings (overridable via CLI)
DEFAULT_VOICE = "bm_daniel"
DEFAULT_SPEED = 1.0

# Daemon startup timeout
DAEMON_START_TIMEOUT = 15.0  # seconds


def daemon_is_running() -> bool:
    """Check if the daemon process is alive."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # Signal 0 = check if process exists
        return True
    except (ProcessLookupError, ValueError, PermissionError):
        return False


def start_daemon() -> bool:
    """Start the daemon in the background and wait for it to be ready.

    Returns True if the daemon is ready, False on timeout.
    """
    # Clean stale socket
    if SOCKET_PATH.exists() and not daemon_is_running():
        SOCKET_PATH.unlink(missing_ok=True)
        PID_FILE.unlink(missing_ok=True)

    # Launch daemon
    subprocess.Popen(
        [sys.executable, str(DAEMON_SCRIPT), "--daemonize"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for socket to appear
    deadline = time.time() + DAEMON_START_TIMEOUT
    while time.time() < deadline:
        if SOCKET_PATH.exists():
            # Brief extra pause to ensure the daemon is accepting connections
            time.sleep(0.1)
            return True
        time.sleep(0.1)

    return False


def ensure_daemon() -> bool:
    """Make sure the daemon is running. Start it if needed.

    Returns True if daemon is ready, False otherwise.
    """
    if SOCKET_PATH.exists() and daemon_is_running():
        return True
    return start_daemon()


def send_to_daemon(message: str, voice: str, speed: float) -> dict:
    """Send a synthesis request to the daemon and return the response."""
    request = {"message": message, "voice": voice, "speed": speed}

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(30.0)  # generous timeout for long utterances
    try:
        sock.connect(str(SOCKET_PATH))
        sock.sendall((json.dumps(request) + "\n").encode("utf-8"))

        # Read response
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        if data.strip():
            return json.loads(data.decode("utf-8").strip())
        return {"status": "ok"}
    except (ConnectionRefusedError, FileNotFoundError):
        return {"status": "error", "detail": "daemon not reachable"}
    finally:
        sock.close()


def speak(message: str, voice: str, speed: float) -> None:
    """Ensure daemon is running, then send the message for synthesis."""
    if not message.strip():
        return

    if not ensure_daemon():
        print("Error: Could not start TTS daemon", file=sys.stderr)
        return

    response = send_to_daemon(message, voice, speed)

    if response.get("status") == "error":
        # If daemon crashed, try once more with a fresh start
        if start_daemon():
            send_to_daemon(message, voice, speed)


def main() -> None:
    parser = argparse.ArgumentParser(description="TTS narrator (Kokoro client)")
    parser.add_argument("--message", "-m", help="Speak this message directly")
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Voice ID (default: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=DEFAULT_SPEED,
        help=f"Speech speed (default: {DEFAULT_SPEED})",
    )
    parser.add_argument(
        "--stop-daemon",
        action="store_true",
        help="Stop the running TTS daemon",
    )
    args = parser.parse_args()

    if args.stop_daemon:
        if daemon_is_running():
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped TTS daemon (pid {pid})")
        else:
            print("No daemon running")
        return

    if args.message:
        speak(args.message, args.voice, args.speed)
    else:
        message = sys.stdin.read().strip()
        speak(message, args.voice, args.speed)


if __name__ == "__main__":
    main()
