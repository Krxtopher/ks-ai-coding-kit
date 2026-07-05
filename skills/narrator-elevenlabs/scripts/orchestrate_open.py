#!/usr/bin/env python3
"""
Cold open orchestrator for the narrator skill.

Reads a cold-open.yaml definition from a personality folder and produces a
radio-show-style opening sequence: continuous music playback with smooth volume
ducking interleaved with TTS narration segments.

Architecture:
    1. Generate TTS audio for each speech segment → save to temp files
    2. Measure durations of each TTS clip
    3. Use ffmpeg to render a single mixed audio file:
       - Music bed with volume automation (duck/swell/fade baked in)
       - TTS clips placed at calculated time offsets
    4. Play the final mix as one continuous piece

This ensures the music never restarts or stutters — all volume transitions
are smooth and continuous.

Usage:
    python orchestrate_open.py --personality-dir ./personalities \\
        --teaser "So. Today we're looking at a Python file..." \\
        --workspace "my-project" \\
        --agent "Kiro"

Environment:
    ELEVENLABS_API_KEY  — required for TTS speech segments.
    ELEVENLABS_VOICE_ID — optional (falls back to config.yaml > default).
    ELEVENLABS_MODEL_ID — optional (falls back to config.yaml > default).

Dependencies:
    - ffmpeg (for audio mixing and volume automation)
    - ffplay or mpv or afplay (for final playback)
    - ffprobe (for measuring TTS clip durations)
    - httpx, pyyaml (Python packages)
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx
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


# ─── TTS generation (to file) ───────────────────────────────────────────────


def generate_tts_to_file(
    text: str,
    output_path: Path,
    api_key: str,
    tts_settings: dict,
) -> bool:
    """Generate TTS audio and save to a file. Returns True on success."""
    voice_id = tts_settings["voice_id"]
    model_id = tts_settings["model_id"]
    speed = tts_settings["speed"]
    stability = tts_settings["stability"]
    similarity_boost = tts_settings["similarity_boost"]
    style = tts_settings["style"]

    text = strip_audio_tags_if_needed(text, model_id)
    if not text:
        return False

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
                    return False
                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=4096):
                        if chunk:
                            f.write(chunk)
        return True
    except httpx.TimeoutException:
        print("Error: ElevenLabs request timed out", file=sys.stderr)
        return False
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


# ─── Audio utilities ─────────────────────────────────────────────────────────


def get_audio_duration(file_path: Path) -> float:
    """Get duration of an audio file in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("Could not get duration for %s: %s", file_path, e)
        return 3.0  # Fallback estimate


def find_player_cmd() -> list[str] | None:
    """Find a suitable audio player for the final mix."""
    if shutil.which("mpv"):
        return ["mpv", "--no-terminal", "--no-video", "--"]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    if shutil.which("afplay"):
        return ["afplay"]
    return None


# ─── Mix rendering ──────────────────────────────────────────────────────────


def render_mix(
    music_path: Path,
    tts_clips: list[dict],
    segments: list[dict],
    music_volume: float,
    output_path: Path,
) -> bool:
    """Render the final mixed audio using ffmpeg.

    Constructs an ffmpeg filter graph that:
    - Applies volume automation to the music track with smooth ramps
    - Places TTS clips at calculated time offsets
    - Mixes everything into a single output file at full volume

    Volume transitions use linear ramps (configurable duration) so ducks
    and swells sound natural rather than jarring.

    tts_clips: list of {"path": Path, "duration": float, "segment_index": int}
    segments: the raw segment list from cold-open.yaml
    """
    # ── Configuration ────────────────────────────────────────────────────
    # Duration of volume ramps (duck-down and swell-up transitions)
    ramp_duration = 0.5  # seconds

    # ── Calculate timeline ───────────────────────────────────────────────
    timeline: list[dict] = []
    current_time = 0.0
    tts_by_index = {clip["segment_index"]: clip for clip in tts_clips}

    # Padding includes ramp time so speech doesn't start during the ramp
    pre_speech_pad = ramp_duration + 0.2  # ramp down + small breath
    post_speech_pad = 0.2 + ramp_duration  # small breath + ramp up

    for i, segment in enumerate(segments):
        seg_type = segment["type"]

        if seg_type == "music-only":
            duration = segment.get("duration", 2.0)
            timeline.append({
                "type": "music-only",
                "start": current_time,
                "duration": duration,
                "volume": music_volume,
            })
            current_time += duration

        elif seg_type == "speech":
            duck_vol = segment.get("duck_volume", 0.15)
            clip_info = tts_by_index.get(i)
            if clip_info is None:
                continue
            speech_duration = clip_info["duration"]

            total_duration = pre_speech_pad + speech_duration + post_speech_pad
            timeline.append({
                "type": "speech",
                "start": current_time,
                "duration": total_duration,
                "duck_volume": duck_vol,
                "tts_path": clip_info["path"],
                "tts_start": current_time + pre_speech_pad,
                "tts_duration": speech_duration,
                "ramp_duration": ramp_duration,
            })
            current_time += total_duration

        elif seg_type == "fade-out":
            duration = segment.get("duration", 2.5)
            timeline.append({
                "type": "fade-out",
                "start": current_time,
                "duration": duration,
                "start_volume": music_volume,
            })
            current_time += duration

    total_duration = current_time

    # ── Build volume envelope as a piecewise expression ──────────────────
    # We build a list of (time, volume) keyframes, then construct a single
    # ffmpeg expression that linearly interpolates between them.

    keyframes: list[tuple[float, float]] = []  # (time, volume)

    for entry in timeline:
        start = entry["start"]
        end = start + entry["duration"]

        if entry["type"] == "music-only":
            vol = entry["volume"]
            # Hold at this volume for the segment
            keyframes.append((start, vol))
            keyframes.append((end, vol))

        elif entry["type"] == "speech":
            duck_vol = entry["duck_volume"]
            ramp = entry["ramp_duration"]
            # Ramp down from music_volume to duck_volume
            keyframes.append((start, music_volume))
            keyframes.append((start + ramp, duck_vol))
            # Hold at duck volume during speech
            keyframes.append((end - ramp, duck_vol))
            # Ramp back up to music_volume
            keyframes.append((end, music_volume))

        elif entry["type"] == "fade-out":
            sv = entry["start_volume"]
            # Linear fade to silence
            keyframes.append((start, sv))
            keyframes.append((end, 0.0))

    # Add a final silence keyframe
    keyframes.append((total_duration + 0.1, 0.0))

    # Deduplicate and sort keyframes by time
    # If two keyframes are at the same time, keep the later one in the list
    keyframes.sort(key=lambda k: k[0])

    # Remove redundant keyframes where consecutive entries are at the same time
    deduped: list[tuple[float, float]] = []
    for kf in keyframes:
        if deduped and abs(kf[0] - deduped[-1][0]) < 0.001:
            deduped[-1] = kf  # overwrite with latest value at same time
        else:
            deduped.append(kf)
    keyframes = deduped

    # Build ffmpeg volume expression using linear interpolation between keyframes
    # Expression form: lerp between adjacent keyframes based on current time (t)
    # We build a nested if() expression that selects the right keyframe pair
    volume_expr_parts: list[str] = []
    for idx in range(len(keyframes) - 1):
        t0, v0 = keyframes[idx]
        t1, v1 = keyframes[idx + 1]

        if abs(v1 - v0) < 0.001:
            # Constant volume segment
            expr = f"if(between(t,{t0:.4f},{t1:.4f}),{v0:.4f}"
        else:
            # Linear interpolation: v0 + (v1-v0) * (t-t0) / (t1-t0)
            dt = t1 - t0
            dv = v1 - v0
            expr = f"if(between(t,{t0:.4f},{t1:.4f}),{v0:.4f}+{dv:.4f}*(t-{t0:.4f})/{dt:.4f}"
        volume_expr_parts.append(expr)

    # Nest right-to-left: if(cond1, val1, if(cond2, val2, ..., 0))
    volume_expr = "0"
    for part in reversed(volume_expr_parts):
        volume_expr = f"{part},{volume_expr})"

    # ── Build ffmpeg command ─────────────────────────────────────────────
    cmd = ["ffmpeg", "-y", "-loglevel", "quiet"]

    # Input 0: music (loop to cover total duration)
    cmd.extend(["-stream_loop", "-1", "-i", str(music_path)])

    # Inputs 1..N: TTS clips
    speech_entries = [e for e in timeline if e["type"] == "speech"]
    for entry in speech_entries:
        cmd.extend(["-i", str(entry["tts_path"])])

    # Build filter graph
    filters: list[str] = []

    # Music: trim, apply smooth volume envelope
    filters.append(
        f"[0:a]atrim=0:{total_duration:.3f},asetpts=PTS-STARTPTS,"
        f"volume='{volume_expr}':eval=frame[music]"
    )

    # TTS clips: delay to correct position, pad to total length
    mix_inputs = ["[music]"]
    for idx, entry in enumerate(speech_entries):
        input_idx = idx + 1
        delay_ms = int(entry["tts_start"] * 1000)
        label = f"tts{idx}"
        filters.append(
            f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},apad=whole_dur={total_duration:.3f}[{label}]"
        )
        mix_inputs.append(f"[{label}]")

    # Mix all streams — use normalize=0 to prevent volume reduction
    n_inputs = len(mix_inputs)
    mix_input_str = "".join(mix_inputs)
    filters.append(
        f"{mix_input_str}amix=inputs={n_inputs}:duration=first"
        f":dropout_transition=0:normalize=0[out]"
    )

    filter_graph = ";".join(filters)
    cmd.extend(["-filter_complex", filter_graph])
    cmd.extend(["-map", "[out]", "-t", f"{total_duration:.3f}", str(output_path)])

    # ── Run ffmpeg ───────────────────────────────────────────────────────
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Error: ffmpeg failed: {result.stderr}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print("Error: ffmpeg timed out", file=sys.stderr)
        return False


# ─── Orchestration engine ───────────────────────────────────────────────────


def run_cold_open(
    config_path: Path,
    teaser: str,
    workspace: str,
    agent: str,
    api_key: str,
    tts_settings: dict,
) -> None:
    """Execute the cold open sequence defined in a cold-open.yaml file."""

    cold_open = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    personality_dir = config_path.parent

    music_file = personality_dir / cold_open["music"]
    if not music_file.exists():
        print(f"Error: Music file not found: {music_file}", file=sys.stderr)
        sys.exit(1)

    music_volume = cold_open.get("music_volume", 0.8)
    segments = cold_open.get("segments", [])

    # Template variables
    template_vars = {
        "teaser": teaser,
        "workspace": workspace,
        "agent": agent,
    }

    # ── Step 1: Generate TTS for speech segments ─────────────────────────
    tts_clips: list[dict] = []
    temp_dir = Path(tempfile.mkdtemp(prefix="narrator_cold_open_"))

    try:
        for i, segment in enumerate(segments):
            if segment["type"] != "speech":
                continue

            text_template = segment.get("text", "")
            text = text_template.format(**template_vars)

            tts_path = temp_dir / f"tts_{i}.mp3"
            success = generate_tts_to_file(text, tts_path, api_key, tts_settings)
            if not success:
                print(f"Error: Failed to generate TTS for segment {i}", file=sys.stderr)
                return

            duration = get_audio_duration(tts_path)
            tts_clips.append({
                "path": tts_path,
                "duration": duration,
                "segment_index": i,
            })

        # ── Step 2: Render the final mix ─────────────────────────────────
        mix_path = temp_dir / "cold_open_mix.mp3"
        success = render_mix(music_file, tts_clips, segments, music_volume, mix_path)
        if not success:
            print("Error: Failed to render cold open mix", file=sys.stderr)
            return

        # ── Step 3: Play the final mix ───────────────────────────────────
        player_cmd = find_player_cmd()
        if player_cmd is None:
            print("Error: No audio player found", file=sys.stderr)
            return

        cmd = player_cmd + [str(mix_path)]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()

    finally:
        # Clean up temp files
        for f in temp_dir.iterdir():
            try:
                f.unlink()
            except OSError:
                pass
        try:
            temp_dir.rmdir()
        except OSError:
            pass


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orchestrate a cold open sequence with music and TTS narration."
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

    # ── Load TTS settings ────────────────────────────────────────────────
    config = load_config()
    tts_settings = resolve_tts_settings(config)

    # ── Run ──────────────────────────────────────────────────────────────
    if args.background:
        pid = os.fork()
        if pid > 0:
            return
        os.setsid()
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
        run_cold_open(config_path, args.teaser, args.workspace, args.agent, api_key, tts_settings)
        os._exit(0)
    else:
        run_cold_open(config_path, args.teaser, args.workspace, args.agent, api_key, tts_settings)


if __name__ == "__main__":
    main()
