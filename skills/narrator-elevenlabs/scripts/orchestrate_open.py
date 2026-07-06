#!/usr/bin/env python3
"""
Cold open orchestrator for the narrator skill — real-time mixer.

Reads a cold-open.yaml definition from a personality folder and produces a
radio-show-style opening sequence: continuous music playback with smooth volume
ducking interleaved with TTS narration segments.

Architecture (real-time mixing via sounddevice):
    1. Load the music bed into memory as a numpy array
    2. Start an OutputStream that plays the music immediately
    3. For each speech segment, stream TTS from ElevenLabs and decode into
       a numpy buffer. As TTS data arrives, the mixer callback applies volume
       ducking to the music and overlays the speech — all in real-time.
    4. After all segments play, apply a smooth fade-out and stop.

This approach eliminates the previous ffmpeg render-to-disk latency. Music
starts playing within milliseconds of invocation, and TTS is overlaid as
soon as the first chunk arrives from the API.

Usage:
    python orchestrate_open.py --personality-dir ./personalities/tal-parody \\
        --teaser "So. Today we're looking at a Python file..." \\
        --workspace "my-project" \\
        --agent "Kiro"

Environment:
    ELEVENLABS_API_KEY  — required for TTS speech segments.
    ELEVENLABS_VOICE_ID — optional (falls back to config.yaml > default).
    ELEVENLABS_MODEL_ID — optional (falls back to config.yaml > default).

Dependencies:
    - sounddevice (PortAudio bindings for real-time playback)
    - numpy (array math for mixing and volume ramps)
    - soundfile (decode music and TTS audio into numpy arrays)
    - httpx (ElevenLabs API streaming)
    - pyyaml (cold-open.yaml parsing)
"""

import argparse
import io
import logging
import os
import re
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import sounddevice as sd
import soundfile as sf
import yaml

# ─── Paths ───────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SKILL_DIR / "config.yaml"

# ─── Defaults (shared with speak.py) ────────────────────────────────────────

API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_VOICE_ID = "4e32WqNVWRquDa1OcRYZ"
DEFAULT_SPEED = 1.0
DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY = 0.75
DEFAULT_STYLE = 0.0
OUTPUT_FORMAT = "mp3_44100_64"

SAMPLE_RATE = 44100
CHANNELS = 2  # Stereo output

ENGINES_WITH_AUDIO_TAGS = {"eleven_v3"}

logger = logging.getLogger(__name__)


# ─── Config ──────────────────────────────────────────────────────────────────


def load_config() -> dict:
    """Load voice/model config from the skill's config.yaml."""
    if CONFIG_FILE.exists():
        try:
            return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError):
            pass
    return {}


def resolve_tts_settings(config: dict) -> dict:
    """Resolve TTS parameters from config > env > defaults."""
    return {
        "voice_id": (
            config.get("voice_id")
            or os.environ.get("ELEVENLABS_VOICE_ID")
            or DEFAULT_VOICE_ID
        ),
        "model_id": (
            config.get("model_id")
            or os.environ.get("ELEVENLABS_MODEL_ID")
            or DEFAULT_MODEL_ID
        ),
        "speed": config.get("speed", DEFAULT_SPEED),
        "stability": config.get("stability", DEFAULT_STABILITY),
        "similarity_boost": config.get("similarity_boost", DEFAULT_SIMILARITY),
        "style": config.get("style", DEFAULT_STYLE),
    }


# ─── Audio tag handling ──────────────────────────────────────────────────────

_AUDIO_TAG_PATTERN = re.compile(r"\[[^\]]{1,50}\]", re.IGNORECASE)


def strip_audio_tags_if_needed(text: str, model_id: str) -> str:
    """Strip audio tags for models that don't support them."""
    if model_id in ENGINES_WITH_AUDIO_TAGS:
        return text
    cleaned = _AUDIO_TAG_PATTERN.sub("", text)
    cleaned = re.sub(r"  +", " ", cleaned)
    return cleaned.strip()


# ─── TTS generation ─────────────────────────────────────────────────────────


def generate_tts_audio(
    text: str,
    api_key: str,
    tts_settings: dict,
) -> np.ndarray | None:
    """Generate TTS audio from ElevenLabs and return as a numpy array.

    Returns a float32 numpy array of shape (samples, channels) at SAMPLE_RATE,
    or None on failure.
    """
    voice_id = tts_settings["voice_id"]
    model_id = tts_settings["model_id"]
    speed = tts_settings["speed"]
    stability = tts_settings["stability"]
    similarity_boost = tts_settings["similarity_boost"]
    style = tts_settings["style"]

    text = strip_audio_tags_if_needed(text, model_id)
    if not text:
        return None

    voice_settings: dict[str, Any] = {
        "stability": stability,
        "similarity_boost": similarity_boost,
        "speed": speed,
    }
    if model_id not in ENGINES_WITH_AUDIO_TAGS:
        voice_settings["style"] = style
        voice_settings["use_speaker_boost"] = True

    url = f"{API_BASE}/text-to-speech/{voice_id}/stream"
    params = {"output_format": OUTPUT_FORMAT}
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            with client.stream("POST", url, params=params, headers=headers, json=body) as response:
                if response.status_code != 200:
                    error_body = response.read().decode("utf-8", errors="replace")
                    print(f"Error: ElevenLabs API returned {response.status_code}: {error_body}", file=sys.stderr)
                    return None
                audio_bytes = b""
                for chunk in response.iter_bytes(chunk_size=4096):
                    if chunk:
                        audio_bytes += chunk

        # Decode MP3 bytes to numpy array
        audio_data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")

        # Ensure stereo
        if audio_data.ndim == 1:
            audio_data = np.column_stack([audio_data, audio_data])

        # Resample if needed (unlikely since we request 44100, but be safe)
        if sr != SAMPLE_RATE:
            # Simple nearest-neighbor resample — adequate for speech
            ratio = SAMPLE_RATE / sr
            n_samples = int(len(audio_data) * ratio)
            indices = np.linspace(0, len(audio_data) - 1, n_samples).astype(int)
            audio_data = audio_data[indices]

        return audio_data

    except httpx.TimeoutException:
        print("Error: ElevenLabs request timed out", file=sys.stderr)
        return None
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error decoding TTS audio: {e}", file=sys.stderr)
        return None


# ─── Real-time mixer ────────────────────────────────────────────────────────


class RealtimeMixer:
    """Multi-track audio mixer using sounddevice OutputStream.

    Plays a music bed continuously while allowing speech tracks to be
    overlaid with smooth volume ducking on the music channel.

    The mixer operates in three states for the music gain:
    - FULL: music at full volume (music_volume)
    - DUCKING: ramping down to duck_volume
    - DUCKED: holding at duck_volume while speech plays
    - UNDUCKING: ramping back up to music_volume
    - FADING: final fade-out to silence

    Volume transitions use linear ramps computed per-sample for maximum
    smoothness.
    """

    def __init__(
        self,
        music_data: np.ndarray,
        music_volume: float = 0.8,
        ramp_duration: float = 0.4,
    ):
        """Initialize the mixer.

        Args:
            music_data: Stereo float32 array at SAMPLE_RATE
            music_volume: Base volume for the music track (0.0-1.0)
            ramp_duration: Duration of volume ramps in seconds
        """
        self.music_data = music_data
        self.music_volume = music_volume
        self.ramp_duration = ramp_duration
        self.ramp_samples = int(ramp_duration * SAMPLE_RATE)

        # Playback position in the music track
        self.music_pos = 0

        # Current music gain (starts at music_volume)
        self.current_gain = music_volume

        # Target gain for ramps
        self.target_gain = music_volume

        # Samples remaining in the current ramp (0 = no ramp active)
        self.ramp_remaining = 0

        # Gain step per sample during a ramp
        self.gain_step = 0.0

        # Speech overlay buffer and position
        self.speech_data: np.ndarray | None = None
        self.speech_pos = 0

        # Whether we're done (all segments played, fade complete)
        self.finished = False

        # Lock for thread-safe access to speech buffer
        self._lock = threading.Lock()

        # Event to signal that speech has finished playing
        self._speech_done = threading.Event()
        self._speech_done.set()  # Initially no speech playing

        # Fade-out state
        self._fading = False

    def _start_ramp(self, target: float) -> None:
        """Begin a gain ramp toward the target volume."""
        if self.ramp_samples == 0:
            self.current_gain = target
            self.target_gain = target
            self.ramp_remaining = 0
            return

        self.target_gain = target
        self.ramp_remaining = self.ramp_samples
        self.gain_step = (target - self.current_gain) / self.ramp_samples

    def duck(self, duck_volume: float) -> None:
        """Duck the music to the specified volume."""
        with self._lock:
            self._start_ramp(duck_volume)

    def unduck(self) -> None:
        """Restore music to full volume."""
        with self._lock:
            self._start_ramp(self.music_volume)

    def fade_out(self, duration: float) -> None:
        """Begin a fade-out to silence over the given duration."""
        with self._lock:
            self._fading = True
            self.ramp_remaining = int(duration * SAMPLE_RATE)
            self.target_gain = 0.0
            if self.ramp_remaining > 0:
                self.gain_step = (0.0 - self.current_gain) / self.ramp_remaining
            else:
                self.current_gain = 0.0

    def set_speech(self, audio_data: np.ndarray) -> None:
        """Load a speech clip for overlay. Resets playback position."""
        with self._lock:
            self.speech_data = audio_data
            self.speech_pos = 0
            self._speech_done.clear()

    def wait_speech_done(self, timeout: float = 60.0) -> bool:
        """Block until current speech clip finishes playing."""
        return self._speech_done.wait(timeout=timeout)

    def callback(self, outdata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        """sounddevice OutputStream callback — mixes music + speech in real-time."""
        if status:
            logger.debug("Stream status: %s", status)

        with self._lock:
            # ── Music track ──────────────────────────────────────────
            music_end = self.music_pos + frames
            if music_end <= len(self.music_data):
                music_chunk = self.music_data[self.music_pos:music_end].copy()
            else:
                # Loop the music if we reach the end
                remaining = len(self.music_data) - self.music_pos
                music_chunk = np.zeros((frames, CHANNELS), dtype=np.float32)
                if remaining > 0:
                    music_chunk[:remaining] = self.music_data[self.music_pos:]
                # Wrap around
                wrapped = frames - remaining
                if wrapped > 0 and len(self.music_data) > 0:
                    wrap_end = min(wrapped, len(self.music_data))
                    music_chunk[remaining:remaining + wrap_end] = self.music_data[:wrap_end]
                music_end = wrapped

            self.music_pos = music_end if music_end <= len(self.music_data) else music_end % max(len(self.music_data), 1)

            # ── Apply gain envelope to music ─────────────────────────
            if self.ramp_remaining > 0:
                # We're in a ramp — compute per-sample gain
                ramp_frames = min(frames, self.ramp_remaining)

                # Build gain array for this chunk
                gain_start = self.current_gain
                gain_end = self.current_gain + self.gain_step * ramp_frames
                gain_ramp = np.linspace(gain_start, gain_end, ramp_frames, dtype=np.float32)

                # Apply ramp portion
                music_chunk[:ramp_frames] *= gain_ramp[:, np.newaxis]

                # Apply flat gain for remaining frames (if chunk extends beyond ramp)
                if ramp_frames < frames:
                    music_chunk[ramp_frames:] *= self.target_gain

                self.current_gain = gain_end
                self.ramp_remaining -= ramp_frames

                if self.ramp_remaining <= 0:
                    self.current_gain = self.target_gain
                    self.ramp_remaining = 0
                    # If fade-out completed, mark as finished
                    if self._fading and self.target_gain == 0.0:
                        self.finished = True
            else:
                # Flat gain — no ramp active
                music_chunk *= self.current_gain

            # ── Speech overlay ───────────────────────────────────────
            if self.speech_data is not None and self.speech_pos < len(self.speech_data):
                speech_end = min(self.speech_pos + frames, len(self.speech_data))
                speech_frames = speech_end - self.speech_pos
                speech_chunk = self.speech_data[self.speech_pos:speech_end]

                # Add speech to music (both are float32, simple sum)
                music_chunk[:speech_frames] += speech_chunk

                self.speech_pos = speech_end

                # Check if speech finished
                if self.speech_pos >= len(self.speech_data):
                    self.speech_data = None
                    self.speech_pos = 0
                    self._speech_done.set()

            # ── Clip to prevent distortion ───────────────────────────
            np.clip(music_chunk, -1.0, 1.0, out=music_chunk)

            outdata[:] = music_chunk


# ─── Async TTS pre-fetching ─────────────────────────────────────────────────


class TtsFuture:
    """Wraps a background TTS generation so we can wait on the result later.

    Fire-and-forget: starts generating TTS in a background thread immediately.
    Call .result() to block until the audio is ready (or None on failure).
    """

    def __init__(self, text: str, api_key: str, tts_settings: dict):
        self._result: np.ndarray | None = None
        self._done = threading.Event()
        self._thread = threading.Thread(
            target=self._generate, args=(text, api_key, tts_settings), daemon=True
        )
        self._thread.start()

    def _generate(self, text: str, api_key: str, tts_settings: dict) -> None:
        self._result = generate_tts_audio(text, api_key, tts_settings)
        self._done.set()

    def result(self, timeout: float = 30.0) -> np.ndarray | None:
        """Block until TTS generation completes. Returns audio array or None."""
        self._done.wait(timeout=timeout)
        return self._result

    def is_ready(self) -> bool:
        """Check if TTS generation has completed without blocking."""
        return self._done.is_set()


# ─── Orchestration engine ───────────────────────────────────────────────────


def run_cold_open(
    config_path: Path,
    teaser: str,
    workspace: str,
    agent: str,
    api_key: str,
    tts_settings: dict,
) -> None:
    """Execute the cold open sequence with real-time mixing.

    Music starts playing immediately. TTS requests are fired concurrently
    during preceding music-only segments so the audio is ready (or nearly
    ready) by the time we need it. Ducking and speech start together — no
    dead air between the volume dip and the voice.
    """
    cold_open = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    personality_dir = config_path.parent

    music_file = personality_dir / cold_open["music"]
    if not music_file.exists():
        print(f"Error: Music file not found: {music_file}", file=sys.stderr)
        sys.exit(1)

    music_volume = cold_open.get("music_volume", 0.8)
    segments = cold_open.get("segments", [])

    # Template variables for speech text
    template_vars = {
        "teaser": teaser,
        "workspace": workspace,
        "agent": agent,
    }

    # ── Load music into memory ───────────────────────────────────────────
    try:
        music_data, sr = sf.read(str(music_file), dtype="float32")
    except Exception as e:
        print(f"Error: Could not load music file: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure stereo
    if music_data.ndim == 1:
        music_data = np.column_stack([music_data, music_data])

    # Resample if needed
    if sr != SAMPLE_RATE:
        ratio = SAMPLE_RATE / sr
        n_samples = int(len(music_data) * ratio)
        indices = np.linspace(0, len(music_data) - 1, n_samples).astype(int)
        music_data = music_data[indices]

    # ── Pre-fetch TTS for all speech segments ────────────────────────────
    # Fire all TTS requests immediately so they generate in parallel with
    # the music intro. By the time we need each clip, it's likely ready.
    tts_futures: dict[int, TtsFuture] = {}
    for i, segment in enumerate(segments):
        if segment["type"] == "speech":
            text_template = segment.get("text", "")
            text = text_template.format(**template_vars)
            tts_futures[i] = TtsFuture(text, api_key, tts_settings)

    # ── Initialize the mixer ─────────────────────────────────────────────
    mixer = RealtimeMixer(
        music_data=music_data,
        music_volume=music_volume,
        ramp_duration=0.4,
    )

    # ── Start the audio stream — music plays immediately ─────────────────
    stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=mixer.callback,
        blocksize=1024,
    )
    stream.start()

    try:
        # ── Walk through segments ────────────────────────────────────
        for i, segment in enumerate(segments):
            if mixer.finished:
                break

            seg_type = segment["type"]

            if seg_type == "music-only":
                # Let the music play at full volume. TTS is generating
                # in the background during this time.
                duration = segment.get("duration", 2.0)
                time.sleep(duration)

            elif seg_type == "speech":
                duck_vol = segment.get("duck_volume", 0.15)

                # Wait for the pre-fetched TTS to be ready
                future = tts_futures.get(i)
                if future is None:
                    continue

                tts_audio = future.result(timeout=30.0)
                if tts_audio is None:
                    # TTS failed — skip this segment
                    continue

                # Duck and start speech simultaneously — no gap
                mixer.duck(duck_vol)
                mixer.set_speech(tts_audio)

                # Wait for speech to finish playing
                mixer.wait_speech_done(timeout=60.0)

                # Small breath after speech ends
                time.sleep(0.15)

                # Unduck the music
                mixer.unduck()
                time.sleep(mixer.ramp_duration)

            elif seg_type == "fade-out":
                duration = segment.get("duration", 2.5)
                mixer.fade_out(duration)
                time.sleep(duration + 0.1)

        # ── Ensure we fade out if not already ────────────────────────
        if not mixer.finished:
            mixer.fade_out(0.5)
            time.sleep(0.6)

    finally:
        stream.stop()
        stream.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orchestrate a cold open sequence with music and TTS narration (real-time mixer)."
    )
    parser.add_argument(
        "--personality-dir",
        type=Path,
        required=True,
        help="Path to the personality directory containing cold-open.yaml and music file",
    )
    parser.add_argument(
        "--teaser",
        required=True,
        help="AI-generated teaser text for the {teaser} placeholder",
    )
    parser.add_argument(
        "--workspace",
        default="workspace",
        help="Workspace directory name for the {workspace} placeholder",
    )
    parser.add_argument(
        "--agent",
        default="Kiro",
        help="AI assistant name for the {agent} placeholder",
    )
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Fork to background — script returns immediately, cold open plays asynchronously",
    )
    args = parser.parse_args()

    # ── Locate cold-open.yaml ────────────────────────────────────────────
    config_path = args.personality_dir / "cold-open.yaml"
    if not config_path.exists():
        # No cold open defined — silent no-op
        return

    # ── Resolve API key ──────────────────────────────────────────────────
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # ── Run ──────────────────────────────────────────────────────────────
    if args.background:
        # Spawn a detached child process instead of forking. os.fork() after
        # threads are created (sounddevice, httpx) causes deadlocks on
        # Python 3.12+ / macOS. Re-invoke the same script without --background.
        import subprocess

        cmd = [
            sys.executable, __file__,
            "--personality-dir", str(args.personality_dir),
            "--teaser", args.teaser,
            "--workspace", args.workspace,
            "--agent", args.agent,
        ]
        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return

    # ── Load TTS settings (only in foreground / child process) ───────────
    config = load_config()
    tts_settings = resolve_tts_settings(config)
    run_cold_open(config_path, args.teaser, args.workspace, args.agent, api_key, tts_settings)


if __name__ == "__main__":
    main()
