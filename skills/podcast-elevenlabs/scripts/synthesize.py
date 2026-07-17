"""Audio synthesis via ElevenLabs Text-to-Speech API.

Handles text-to-speech conversion for podcast segments using the ElevenLabs
Python SDK. Supports v3 (with audio tag direction) and v2/v2.5 models
(audio tags stripped automatically).

Usage as a module:
    from synthesize import synthesize_segments, synthesize_segment

    segments = synthesize_segments(
        api_key="your-api-key",
        script=[{"speaker": "voice1", "text": "[excited] Hello!"}],
        voice1_id="JBFqnCBsd6RMkjVDRZzb",
        voice2_id="nPczCjzI2devNBz1zQrb",
        model="eleven_v3",
    )
"""

from __future__ import annotations

import logging
import re
import time

from elevenlabs import ElevenLabs, VoiceSettings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "eleven_v3"

# Models that support audio tags natively.
# All others get tags stripped before synthesis.
AUDIO_TAG_MODELS = {"eleven_v3"}

# Regex to match ElevenLabs audio tags: [tag text]
# Matches square-bracketed directives like [laughs], [excited], [whispers]
_AUDIO_TAG_PATTERN = re.compile(r"\[([^\[\]]+)\]\s*")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def strip_audio_tags(text: str) -> str:
    """Remove ElevenLabs audio tags from text for models that don't support them.

    Strips patterns like [laughs], [excited], [whispers] etc.
    Preserves IPA pronunciation (in /slashes/) and all other text.

    Args:
        text: Input text potentially containing audio tags.

    Returns:
        Text with audio tags removed and whitespace normalized.
    """
    cleaned = _AUDIO_TAG_PATTERN.sub("", text)
    # Normalize any double spaces left behind
    cleaned = re.sub(r"  +", " ", cleaned).strip()
    return cleaned


def _create_client(api_key: str) -> ElevenLabs:
    """Create an ElevenLabs SDK client instance.

    Args:
        api_key: ElevenLabs API key.

    Returns:
        Configured ElevenLabs client.
    """
    return ElevenLabs(api_key=api_key)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def synthesize_segment(
    api_key: str,
    voice_id: str,
    text: str,
    model: str = DEFAULT_MODEL,
    output_format: str = "mp3_44100_128",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    speed: float = 1.0,
) -> bytes | None:
    """Synthesize a single text segment and return raw audio bytes.

    For models that don't support audio tags (anything not in AUDIO_TAG_MODELS),
    tags like [excited] or [laughs] are automatically stripped before sending
    to the API. Returns None if the text is empty after processing.

    Args:
        api_key: ElevenLabs API key.
        voice_id: ElevenLabs voice ID (e.g. "JBFqnCBsd6RMkjVDRZzb").
        text: The text to synthesize. May include audio tags like [laughs],
              [whispers], or IPA pronunciation in /slashes/.
        model: ElevenLabs model ID (e.g. "eleven_v3", "eleven_flash_v2_5",
               "eleven_multilingual_v2").
        output_format: Audio output format. Options include:
            mp3_44100_128, mp3_44100_192, mp3_22050_32, pcm_16000, pcm_22050
        stability: Voice stability (0.0-1.0). Lower = more expressive.
        similarity_boost: Voice clarity/similarity (0.0-1.0).
        style: Style exaggeration (0.0-1.0). Higher = more stylistic.
        speed: Speech speed multiplier (0.7-1.2).

    Returns:
        Raw audio bytes in the specified format (MP3 by default).

    Raises:
        Exception: If the ElevenLabs API returns an error.
    """
    client = _create_client(api_key)

    # Strip audio tags for models that don't support them
    synth_text = text if model in AUDIO_TAG_MODELS else strip_audio_tags(text)

    if not synth_text.strip():
        logger.warning("Empty text after processing, skipping synthesis")
        return None

    response = client.text_to_speech.convert(
        voice_id=voice_id,
        text=synth_text,
        model_id=model,
        output_format=output_format,
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            speed=speed,
        ),
    )

    # The SDK returns an iterator of bytes chunks
    audio_bytes = b"".join(chunk for chunk in response if chunk)
    return audio_bytes


def synthesize_segments(
    api_key: str,
    script: list[dict],
    voice1_id: str,
    voice2_id: str,
    model: str = DEFAULT_MODEL,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    speed: float = 1.0,
) -> list[bytes]:
    """Synthesize all script turns sequentially.

    Iterates through the script, mapping each turn's "speaker" field to the
    appropriate voice ID, and synthesizes the audio. Progress is logged to
    stdout.

    For v2 models, audio tags in the script text are automatically stripped
    before synthesis (handled by synthesize_segment).

    Args:
        api_key: ElevenLabs API key.
        script: List of dicts with "speaker" ("voice1"/"voice2") and "text" keys.
                Text may include ElevenLabs audio tags (e.g. [excited], [whispers])
                and IPA pronunciation (e.g. /ˈwɜːrd/).
        voice1_id: ElevenLabs voice ID for voice 1.
        voice2_id: ElevenLabs voice ID for voice 2.
        model: ElevenLabs model ID.
        stability: Voice stability (0.0-1.0).
        similarity_boost: Voice clarity/similarity (0.0-1.0).
        style: Style exaggeration (0.0-1.0).
        speed: Speech speed multiplier (0.7-1.2).

    Returns:
        List of audio byte segments in the same order as the script.

    Raises:
        Exception: If any synthesis call fails.
    """
    total = len(script)
    segments: list[bytes] = []

    if model not in AUDIO_TAG_MODELS:
        logger.info(
            "Model '%s' does not support audio tags — they will be stripped",
            model,
        )

    for i, entry in enumerate(script, 1):
        speaker = entry["speaker"]
        text = entry["text"]
        voice_id = voice1_id if speaker == "voice1" else voice2_id

        print(f"      Segment {i}/{total} ({speaker})...", end=" ", flush=True)

        start = time.perf_counter()
        audio = synthesize_segment(
            api_key=api_key,
            voice_id=voice_id,
            text=text,
            model=model,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            speed=speed,
        )
        elapsed = time.perf_counter() - start

        if audio is None:
            print(f"SKIPPED (empty text)")
            continue

        segments.append(audio)
        print(f"OK ({len(audio):,} bytes, {elapsed:.1f}s)")

    return segments
