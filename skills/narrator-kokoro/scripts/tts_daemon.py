#!/usr/bin/env python3
"""
Persistent TTS daemon using Kokoro (local ONNX model).

Loads the model once and listens on a Unix socket for synthesis requests.
Auto-exits after a configurable idle timeout to avoid lingering forever.

Protocol (over Unix socket):
    Client sends a JSON object followed by a newline:
        {"message": "text to speak", "voice": "af_sarah", "speed": 1.0}
    Server responds with a JSON object followed by a newline:
        {"status": "ok"} or {"status": "error", "detail": "..."}

The daemon handles playback internally (via afplay) with serialized queue.

Usage:
    python3 tts_daemon.py              # Run in foreground (for debugging)
    python3 tts_daemon.py --daemonize  # Fork to background
"""

import argparse
import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_PATH = SCRIPT_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = SCRIPT_DIR / "voices-v1.0.bin"

SOCKET_PATH = Path(tempfile.gettempdir()) / "kiro-tts-daemon.sock"
PID_FILE = Path(tempfile.gettempdir()) / "kiro-tts-daemon.pid"
LOCK_FILE = Path(tempfile.gettempdir()) / "kiro-tts-narrator.lock"

IDLE_TIMEOUT_SECONDS = 600  # 10 minutes
DEFAULT_VOICE = "af_sarah"
DEFAULT_SPEED = 1.0
DEFAULT_LANG = "en-us"

# ─── Globals ─────────────────────────────────────────────────────────────────

kokoro: Kokoro | None = None
last_activity: float = 0.0
shutdown_event = threading.Event()


def load_model() -> Kokoro:
    """Load the Kokoro model."""
    if not MODEL_PATH.exists():
        print(f"Error: Model not found at {MODEL_PATH}", file=sys.stderr)
        sys.exit(1)
    if not VOICES_PATH.exists():
        print(f"Error: Voices not found at {VOICES_PATH}", file=sys.stderr)
        sys.exit(1)
    return Kokoro(str(MODEL_PATH), str(VOICES_PATH))


def play_audio(tmp_path: str) -> None:
    """Play a WAV file with serialized locking, then clean up."""
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


def synthesize(message: str, voice: str, speed: float) -> str | None:
    """Synthesize speech to a temp WAV file. Returns the file path, or None on empty input."""
    if not message.strip():
        return None

    samples, sample_rate = kokoro.create(message, voice=voice, speed=speed, lang=DEFAULT_LANG)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, samples, sample_rate)
        return tmp.name


def handle_client(conn: socket.socket) -> None:
    """Handle a single client connection."""
    global last_activity
    last_activity = time.time()

    try:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        if not data.strip():
            return

        request = json.loads(data.decode("utf-8").strip())
        message = request.get("message", "")
        voice = request.get("voice", DEFAULT_VOICE)
        speed = request.get("speed", DEFAULT_SPEED)

        if not message.strip():
            response = {"status": "ok", "detail": "empty message, skipped"}
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        else:
            # Synthesize (blocking) — this is the ~800ms part
            wav_path = synthesize(message, voice, speed)
            # Respond to client immediately (unblock the caller)
            response = {"status": "ok"}
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
            conn.close()
            conn = None  # prevent double-close in finally
            # Play audio asynchronously in a background thread
            if wav_path:
                t = threading.Thread(target=play_audio, args=(wav_path,), daemon=True)
                t.start()

    except Exception as e:
        try:
            error_resp = {"status": "error", "detail": str(e)}
            conn.sendall((json.dumps(error_resp) + "\n").encode("utf-8"))
        except OSError:
            pass
    finally:
        if conn is not None:
            conn.close()


def idle_watchdog() -> None:
    """Monitor idle time and trigger shutdown if exceeded."""
    while not shutdown_event.is_set():
        time.sleep(30)
        if time.time() - last_activity > IDLE_TIMEOUT_SECONDS:
            shutdown_event.set()
            break


def cleanup() -> None:
    """Remove socket and PID files."""
    try:
        SOCKET_PATH.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def run_server() -> None:
    """Main server loop."""
    global kokoro, last_activity

    # Clean up stale socket
    SOCKET_PATH.unlink(missing_ok=True)

    # Load model
    kokoro = load_model()
    last_activity = time.time()

    # Write PID file
    PID_FILE.write_text(str(os.getpid()))

    # Create Unix socket
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET_PATH))
    server.listen(5)
    server.settimeout(5.0)  # Allow periodic check of shutdown_event

    # Start idle watchdog
    watchdog = threading.Thread(target=idle_watchdog, daemon=True)
    watchdog.start()

    # Handle SIGTERM gracefully
    def handle_sigterm(signum, frame):
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    try:
        while not shutdown_event.is_set():
            try:
                conn, _ = server.accept()
                # Handle each client in a thread so the server stays responsive
                t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break
    finally:
        server.close()
        cleanup()


def daemonize() -> None:
    """Fork to background as a proper daemon."""
    # First fork
    pid = os.fork()
    if pid > 0:
        # Parent waits briefly for socket to appear
        for _ in range(50):  # 5 seconds max
            time.sleep(0.1)
            if SOCKET_PATH.exists():
                return
        return

    # Child — new session
    os.setsid()

    # Second fork (prevent terminal reacquisition)
    pid = os.fork()
    if pid > 0:
        os._exit(0)

    # Grandchild — redirect stdio
    sys.stdin.close()
    devnull = open(os.devnull, "w")
    sys.stdout = devnull
    sys.stderr = devnull

    run_server()
    os._exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kokoro TTS daemon")
    parser.add_argument(
        "--daemonize", action="store_true", help="Fork to background"
    )
    parser.add_argument(
        "--stop", action="store_true", help="Stop a running daemon"
    )
    args = parser.parse_args()

    if args.stop:
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to daemon (pid {pid})")
            except (ProcessLookupError, ValueError):
                print("Daemon not running (stale PID file)")
                cleanup()
        else:
            print("No daemon PID file found")
        return

    if args.daemonize:
        daemonize()
    else:
        run_server()


if __name__ == "__main__":
    main()
