"""Audio synthesis via Amazon Polly generative engine.

Handles text-to-speech conversion for podcast segments. Supports an optional
custom Polly endpoint URL for beta/preview features like voice cloning.

Usage as a module:
    from synthesize import synthesize_segments, synthesize_segment

    segments = synthesize_segments(
        session=boto3.Session(),
        script=[{"speaker": "voice1", "text": "Hello!"}],
        voice1_id="Matthew",
        voice2_id="Danielle",
    )
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AWS_REGION = "us-east-1"
CHUNK_SIZE = 4096


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_polly_client(
    session: boto3.Session,
    endpoint_url: Optional[str] = None,
) -> "botocore.client.Polly":
    """Create a Polly client, optionally targeting a custom endpoint.

    Args:
        session: A boto3 session (optionally configured with a specific profile).
        endpoint_url: Optional custom Polly endpoint URL. When None, the
                      standard public Polly endpoint is used.

    Returns:
        A configured Polly client.
    """
    kwargs: dict = {"region_name": AWS_REGION}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    return session.client("polly", **kwargs)


def synthesize_segment(
    client,
    voice_id: str,
    text: str,
    engine: str = "generative",
    output_format: str = "mp3",
    sample_rate: str = "24000",
) -> bytes:
    """Synthesize a single text segment and return raw audio bytes.

    Args:
        client: A configured Polly client.
        voice_id: Polly voice ID (e.g. "Matthew", "vc-56f8fbd479").
        text: The text to synthesize.
        engine: Polly engine to use ("generative", "neural", "standard").
        output_format: Audio format ("mp3", "ogg_vorbis", "pcm").
        sample_rate: Sample rate in Hz as a string.

    Returns:
        Raw audio bytes in the specified format.
    """
    response = client.synthesize_speech(
        Engine=engine,
        OutputFormat=output_format,
        SampleRate=sample_rate,
        Text=text,
        VoiceId=voice_id,
    )

    stream = response["AudioStream"]
    audio_data = bytearray()
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        audio_data.extend(chunk)

    return bytes(audio_data)


def synthesize_segments(
    session: boto3.Session,
    script: list[dict],
    voice1_id: str,
    voice2_id: str,
    endpoint_url: Optional[str] = None,
    engine: str = "generative",
) -> list[bytes]:
    """Synthesize all script turns sequentially.

    Args:
        session: A boto3 session.
        script: List of dicts with "speaker" ("voice1"/"voice2") and "text" keys.
        voice1_id: Polly voice ID for voice 1.
        voice2_id: Polly voice ID for voice 2.
        endpoint_url: Optional custom Polly endpoint URL.
        engine: Polly engine to use.

    Returns:
        List of audio byte segments in the same order as the script.
    """
    client = get_polly_client(session, endpoint_url)
    voice_map = {"voice1": voice1_id, "voice2": voice2_id}
    segments: list[bytes] = []

    total = len(script)
    total_bytes = 0
    synth_start = time.perf_counter()

    for i, entry in enumerate(script, 1):
        speaker_key = entry["speaker"]
        voice_id = voice_map[speaker_key]
        text = entry["text"]

        logger.info(
            f"Segment {i}/{total} — {speaker_key} ({voice_id}): "
            f"{text[:50]}{'...' if len(text) > 50 else ''}"
        )

        seg_start = time.perf_counter()
        audio_bytes = synthesize_segment(client, voice_id, text, engine=engine)
        seg_time = time.perf_counter() - seg_start

        segments.append(audio_bytes)
        total_bytes += len(audio_bytes)

        logger.info(f"  -> {len(audio_bytes):,} bytes in {seg_time:.2f}s")

    total_time = time.perf_counter() - synth_start
    logger.info(
        f"Synthesis complete: {total} segments, "
        f"{total_bytes:,} bytes total, {total_time:.1f}s elapsed"
    )

    return segments
