"""Audio mixing pipeline for podcast generation.

Handles intro/outro music mixing, segment concatenation with pauses,
volume ducking, and fade effects. Built on pydub (requires ffmpeg).

Usage as a module:
    from mixer import assemble_podcast, mix_intro, mix_outro

    final_audio = assemble_podcast(
        segments=[b"...", b"..."],
        intro_music_path=Path("assets/intro.mp3"),
        intro_speeches=[b"..."],
        outro_speech=b"...",
    )
    Path("podcast.mp3").write_bytes(final_audio)
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timing & volume constants (milliseconds / decibels)
# ---------------------------------------------------------------------------

INTRO_MUSIC_DURATION_MS = 2000      # Full-volume music before first speech
DUCK_VOLUME_DB = -12                # Volume reduction when speech plays over music
DUCK_RAMP_MS = 1000                 # Smooth ramp into/out of ducked level
INTRO_RAMP_BACK_MS = 3000           # Full-volume music between intro speech segments
INTRO_FADE_OUT_MS = 2000            # Music fade-out after intro speech
SEGMENT_PAUSE_MS = 400              # Silence between conversation turns
OUTRO_PAUSE_MS = 650                # Silence before outro music begins
OUTRO_FADE_IN_MS = 2500             # Outro music fade-in duration
OUTRO_FULL_VOLUME_MS = 3000         # Full-volume outro tail before final fade-out
OUTRO_TAIL_FADE_MS = 800            # Final fade-out of outro


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assemble_podcast(
    segments: list[bytes],
    intro_music_path: Path | None = None,
    intro_speeches: list[bytes] | None = None,
    outro_speech: bytes | None = None,
    music_volume_pct: int = 100,
) -> bytes:
    """Assemble a complete podcast from synthesized segments and optional music.

    Args:
        segments: List of MP3 byte segments (the conversation turns).
        intro_music_path: Path to an MP3 file used for intro and outro music.
                         If None, segments are concatenated without music.
        intro_speeches: Optional list of MP3 byte segments for spoken intro lines
                       (played over ducked intro music).
        outro_speech: Optional MP3 bytes for the spoken outro/sign-off
                     (played over ducked outro music).
        music_volume_pct: Music volume as a percentage (1-100). 100 = full volume.

    Returns:
        Final mixed podcast as MP3 bytes.
    """
    from pydub import AudioSegment

    music_vol_db = _pct_to_db(music_volume_pct)

    if intro_music_path and intro_music_path.exists():
        logger.info("Mixing intro music...")
        intro_and_conversation = mix_intro(
            segments, intro_music_path, intro_speeches, music_vol_db
        )

        if outro_speech:
            logger.info("Mixing outro music...")
            outro_audio = mix_outro(outro_speech, intro_music_path, music_vol_db)

            combined = AudioSegment.from_mp3(io.BytesIO(intro_and_conversation))
            outro_pause = AudioSegment.silent(duration=OUTRO_PAUSE_MS)
            outro_part = AudioSegment.from_mp3(io.BytesIO(outro_audio))
            final = combined + outro_pause + outro_part
        else:
            final = AudioSegment.from_mp3(io.BytesIO(intro_and_conversation))
    else:
        # No music — just concatenate segments with pauses
        logger.info("No intro music provided — concatenating segments directly.")
        pause = AudioSegment.silent(duration=SEGMENT_PAUSE_MS)
        final = AudioSegment.empty()
        for i, seg_bytes in enumerate(segments):
            segment = AudioSegment.from_mp3(io.BytesIO(seg_bytes))
            if i > 0:
                final = final + pause
            final = final + segment

    output_buffer = io.BytesIO()
    final.export(output_buffer, format="mp3", bitrate="128k")
    result = output_buffer.getvalue()

    duration_secs = len(final) / 1000.0
    logger.info(
        f"Assembly complete: {duration_secs:.1f}s duration, "
        f"{len(result):,} bytes"
    )
    return result


def mix_intro(
    podcast_segments: list[bytes],
    intro_music_path: Path,
    intro_speeches: list[bytes] | None = None,
    music_volume_db: float = 0.0,
) -> bytes:
    """Mix intro music with podcast segments.

    Sequence (when speech segments are provided):
        1. Music at full volume for INTRO_MUSIC_DURATION_MS
        2. For each speech segment:
           a. Music ducks smoothly
           b. Speech plays over ducked music
           c. If not the last speech: music ramps back to full, holds briefly
        3. Music fades out to silence
        4. Conversation segments play without music

    Returns the complete intro + conversation as MP3 bytes.
    """
    from pydub import AudioSegment

    music = _load_and_prepare_music(intro_music_path, music_volume_db, duration_ms=30000)
    pos = 0

    # Phase 1: Full-volume music lead-in
    final = music[pos:pos + INTRO_MUSIC_DURATION_MS]
    pos += INTRO_MUSIC_DURATION_MS

    if intro_speeches:
        for i, speech_bytes in enumerate(intro_speeches):
            speech_audio = AudioSegment.from_mp3(io.BytesIO(speech_bytes))
            speech_duration_ms = len(speech_audio)

            # Duck ramp: full -> ducked
            ramp_down = music[pos:pos + DUCK_RAMP_MS]
            ramp_down = ramp_down.fade(
                from_gain=0,
                to_gain=DUCK_VOLUME_DB,
                start=0,
                end=len(ramp_down),
            )
            final = final + ramp_down
            pos += DUCK_RAMP_MS

            # Ducked music under speech
            ducked_section = music[pos:pos + speech_duration_ms] + DUCK_VOLUME_DB
            speech_over_music = ducked_section.overlay(speech_audio)
            final = final + speech_over_music
            pos += speech_duration_ms

            # Between speeches: ramp back to full volume, hold
            if i < len(intro_speeches) - 1:
                ramp_up = music[pos:pos + DUCK_RAMP_MS]
                ramp_up = ramp_up.fade(
                    from_gain=DUCK_VOLUME_DB,
                    to_gain=0,
                    start=0,
                    end=len(ramp_up),
                )
                final = final + ramp_up
                pos += DUCK_RAMP_MS

                full_hold = music[pos:pos + INTRO_RAMP_BACK_MS]
                final = final + full_hold
                pos += INTRO_RAMP_BACK_MS

        # After last speech: fade out from ducked level
        fade_section = music[pos:pos + INTRO_FADE_OUT_MS] + DUCK_VOLUME_DB
        fade_section = fade_section.fade_out(INTRO_FADE_OUT_MS)
        final = final + fade_section
    else:
        # No spoken intro — fade out music directly
        fade_section = music[pos:pos + INTRO_FADE_OUT_MS]
        fade_section = fade_section.fade_out(INTRO_FADE_OUT_MS)
        final = final + fade_section

    # Append conversation segments with pauses
    pause = AudioSegment.silent(duration=SEGMENT_PAUSE_MS)
    for i, seg_bytes in enumerate(podcast_segments):
        segment = AudioSegment.from_mp3(io.BytesIO(seg_bytes))
        if i > 0:
            final = final + pause
        final = final + segment

    output_buffer = io.BytesIO()
    final.export(output_buffer, format="mp3", bitrate="128k")
    return output_buffer.getvalue()


def mix_outro(
    outro_speech: bytes,
    intro_music_path: Path,
    music_volume_db: float = 0.0,
) -> bytes:
    """Mix outro music with the sign-off speech.

    Sequence:
        1. Music fades in from silence to full volume
        2. Music holds at full volume briefly
        3. Music ducks smoothly
        4. Outro speech plays over ducked music
        5. Music ramps back to full volume
        6. Music plays at full volume then fades out

    Returns the outro section as MP3 bytes.
    """
    from pydub import AudioSegment

    speech_audio = AudioSegment.from_mp3(io.BytesIO(outro_speech))
    speech_duration_ms = len(speech_audio)

    full_hold_ms = 2000
    total_music_ms = (
        OUTRO_FADE_IN_MS + full_hold_ms + DUCK_RAMP_MS +
        speech_duration_ms + DUCK_RAMP_MS + OUTRO_FULL_VOLUME_MS
    )

    music = _load_and_prepare_music(intro_music_path, music_volume_db, duration_ms=total_music_ms)
    # Use the tail end of the music for continuity
    outro_music = music[-total_music_ms:]
    pos = 0

    # Phase 1: Fade in
    fade_in_section = outro_music[pos:pos + OUTRO_FADE_IN_MS]
    fade_in_section = fade_in_section.fade_in(OUTRO_FADE_IN_MS)
    pos += OUTRO_FADE_IN_MS

    # Phase 2: Full volume hold
    full_hold_section = outro_music[pos:pos + full_hold_ms]
    pos += full_hold_ms

    # Phase 3: Duck ramp
    duck_ramp_section = outro_music[pos:pos + DUCK_RAMP_MS]
    duck_ramp_section = duck_ramp_section.fade(
        from_gain=0,
        to_gain=DUCK_VOLUME_DB,
        start=0,
        end=len(duck_ramp_section),
    )
    pos += DUCK_RAMP_MS

    # Phase 4: Speech over ducked music
    ducked_section = outro_music[pos:pos + speech_duration_ms] + DUCK_VOLUME_DB
    speech_over_music = ducked_section.overlay(speech_audio)
    pos += speech_duration_ms

    # Phase 5: Ramp back up
    ramp_section = outro_music[pos:pos + DUCK_RAMP_MS]
    ramp_section = ramp_section.fade(
        from_gain=DUCK_VOLUME_DB,
        to_gain=0,
        start=0,
        end=len(ramp_section),
    )
    pos += DUCK_RAMP_MS

    # Phase 6: Full volume tail with fade-out
    tail_section = outro_music[pos:pos + OUTRO_FULL_VOLUME_MS]
    tail_section = tail_section.fade_out(OUTRO_TAIL_FADE_MS)

    # Assemble
    outro = (
        fade_in_section + full_hold_section + duck_ramp_section +
        speech_over_music + ramp_section + tail_section
    )

    output_buffer = io.BytesIO()
    outro.export(output_buffer, format="mp3", bitrate="128k")
    return output_buffer.getvalue()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _pct_to_db(pct: int) -> float:
    """Convert a volume percentage (1-100) to a dB attenuation value."""
    import math
    pct = max(1, min(100, pct))
    if pct >= 100:
        return 0.0
    return 20 * math.log10(pct / 100.0)


def _load_and_prepare_music(
    path: Path,
    volume_db: float,
    duration_ms: int,
) -> "AudioSegment":
    """Load music file, apply volume adjustment, and loop if needed."""
    from pydub import AudioSegment

    music = AudioSegment.from_mp3(str(path))
    if volume_db != 0.0:
        music = music + volume_db
    if len(music) < duration_ms:
        loops = (duration_ms // len(music)) + 1
        music = music * loops
    return music


# ---------------------------------------------------------------------------
# Audio normalization (EBU R128)
# ---------------------------------------------------------------------------


def normalize_audio(audio_bytes: bytes, target_lufs: float = -14.0) -> bytes:
    """Normalize audio to a target loudness using EBU R128 (two-pass loudnorm).

    Uses ffmpeg's loudnorm filter in two passes:
    1. First pass measures the audio's current loudness characteristics.
    2. Second pass applies linear normalization to the target LUFS.

    This produces broadcast-standard loudness suitable for podcast platforms.

    Args:
        audio_bytes: Raw MP3 audio bytes.
        target_lufs: Target integrated loudness in LUFS. Default: -14.0
                     (standard for podcasts and streaming platforms).

    Returns:
        Normalized MP3 audio bytes.

    Raises:
        RuntimeError: If ffmpeg fails during normalization.
    """
    import json
    import subprocess
    import tempfile

    if not audio_bytes:
        return audio_bytes

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        tmp_in_path = tmp_in.name

    tmp_out_path = tmp_in_path.replace(".mp3", "_norm.mp3")

    try:
        # Pass 1: Measure loudness
        measure_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-i", tmp_in_path,
            "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", "-"
        ]
        result = subprocess.run(
            measure_cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg loudnorm measurement failed: {result.stderr[-500:]}")

        # Parse loudnorm stats from stderr (ffmpeg outputs filter info there)
        stderr = result.stderr
        # Find the JSON block output by loudnorm
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            raise RuntimeError("Could not parse loudnorm measurement output")

        stats = json.loads(stderr[json_start:json_end])

        # Pass 2: Apply normalization with measured values
        loudnorm_filter = (
            f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:"
            f"measured_I={stats['input_i']}:"
            f"measured_LRA={stats['input_lra']}:"
            f"measured_TP={stats['input_tp']}:"
            f"measured_thresh={stats['input_thresh']}:"
            f"offset={stats['target_offset']}:"
            f"linear=true:print_format=summary"
        )

        normalize_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-i", tmp_in_path,
            "-af", loudnorm_filter,
            "-ar", "44100", "-b:a", "128k",
            tmp_out_path,
        ]
        result = subprocess.run(
            normalize_cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg loudnorm normalization failed: {result.stderr[-500:]}")

        # Read normalized output
        from pathlib import Path as _Path
        normalized = _Path(tmp_out_path).read_bytes()
        return normalized

    finally:
        import os
        os.unlink(tmp_in_path)
        if os.path.exists(tmp_out_path):
            os.unlink(tmp_out_path)
