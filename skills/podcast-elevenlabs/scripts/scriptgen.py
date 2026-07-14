"""Podcast script generation via Amazon Bedrock.

Takes a content summary and produces a multi-turn conversational podcast
script in JSON format using an LLM (Claude via Bedrock).

Usage as a module:
    from scriptgen import generate_script

    script = generate_script(
        session=boto3.Session(),
        content_summary="Your content here...",
        voice1_name="Matthew",
        voice2_name="Danielle",
        word_budget=300,
    )
    # Returns: [{"speaker": "voice1", "text": "..."}, ...]
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AWS_REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-opus-4-6-v1"
PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "assets" / "prompt_template.txt"
VOICE1_PERSONALITY_PATH = Path(__file__).parent.parent / "assets" / "voice1_personality.txt"
VOICE2_PERSONALITY_PATH = Path(__file__).parent.parent / "assets" / "voice2_personality.txt"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_script(
    session: boto3.Session,
    content_summary: str,
    voice1_name: str = "Matthew",
    voice2_name: str = "Danielle",
    title: str = "Podcast",
    word_budget: int = 300,
    model_id: str | None = None,
    use_thinking: bool = False,
    voice1_personality: str | None = None,
    voice2_personality: str | None = None,
) -> list[dict]:
    """Generate a podcast script from a content summary using Bedrock.

    Args:
        session: A boto3 session (optionally configured with a specific profile).
        content_summary: The pre-processed content to turn into a podcast.
        voice1_name: Display name for the lead presenter.
        voice2_name: Display name for the co-presenter.
        title: Episode title (used for context in the prompt).
        word_budget: Approximate total word count for the conversation.
        model_id: Override the default Bedrock model ID.
        use_thinking: Enable adaptive thinking for potentially better scripts.
        voice1_personality: Override personality description for voice 1.
        voice2_personality: Override personality description for voice 2.

    Returns:
        A list of dicts, each with "speaker" ("voice1"/"voice2") and "text" keys.

    Raises:
        ValueError: If the model output cannot be parsed or is structurally invalid.
    """
    client = session.client("bedrock-runtime", region_name=AWS_REGION)
    effective_model = model_id or MODEL_ID

    # Load personality defaults if not overridden
    v1_personality = voice1_personality or _load_personality(VOICE1_PERSONALITY_PATH)
    v2_personality = voice2_personality or _load_personality(VOICE2_PERSONALITY_PATH)

    prompt = _build_prompt(
        voice1_name=voice1_name,
        voice2_name=voice2_name,
        content_summary=content_summary,
        title=title,
        word_budget=word_budget,
        voice1_personality=v1_personality,
        voice2_personality=v2_personality,
    )

    logger.info(
        f"Generating script: model={effective_model}, "
        f"budget={word_budget} words, thinking={use_thinking}"
    )

    converse_kwargs: dict = {
        "modelId": effective_model,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {
            "maxTokens": 16000 if use_thinking else 4096,
            "temperature": 0.8,
        },
    }

    if use_thinking:
        converse_kwargs["inferenceConfig"]["temperature"] = 1.0
        converse_kwargs["additionalModelRequestFields"] = {
            "thinking": {"type": "adaptive"},
        }

    response = client.converse(**converse_kwargs)

    # Extract text from response (skip thinking blocks if present)
    content_blocks = response["output"]["message"]["content"]
    output_text = ""
    for block in content_blocks:
        if "text" in block:
            output_text = block["text"].strip()
            break

    if not output_text:
        raise ValueError("No text content in model response.")

    script = _parse_script_json(output_text)
    _validate_script(script)

    logger.info(f"Script generated: {len(script)} turns")
    return script


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_personality(path: Path) -> str:
    """Load a personality description from a file."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _build_prompt(
    voice1_name: str,
    voice2_name: str,
    content_summary: str,
    title: str,
    word_budget: int,
    voice1_personality: str,
    voice2_personality: str,
) -> str:
    """Build the Bedrock prompt from the external template."""
    # Calculate recommended turn range from word budget (~25-35 words per turn)
    min_turns = max(6, word_budget // 35)
    max_turns = max(8, word_budget // 25)

    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

    return template.format(
        title=title,
        voice1_name=voice1_name,
        voice2_name=voice2_name,
        content_summary=content_summary,
        min_turns=min_turns,
        max_turns=max_turns,
        word_budget=word_budget,
        voice1_personality=voice1_personality,
        voice2_personality=voice2_personality,
    )


def _parse_script_json(raw_output: str) -> list[dict]:
    """Extract and parse the JSON array from model output.

    Handles common LLM output quirks: markdown fences, preamble text, etc.
    """
    text = raw_output.strip()

    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:\w*)\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find the JSON array if surrounded by extra text
    if not text.startswith("["):
        array_start = text.find("[")
        if array_start != -1:
            text = text[array_start:]

    if not text.endswith("]"):
        array_end = text.rfind("]")
        if array_end != -1:
            text = text[: array_end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse model output as JSON: {e}\n"
            f"  Raw output (first 500 chars):\n{text[:500]}"
        ) from e


def _validate_script(script: list[dict]) -> None:
    """Validate the parsed script structure."""
    if not isinstance(script, list):
        raise ValueError(f"Expected a JSON array, got {type(script).__name__}")

    if len(script) < 4:
        raise ValueError(
            f"Expected at least 4 turns, got {len(script)}. "
            "The content summary may be too short for a meaningful conversation."
        )

    for i, entry in enumerate(script):
        if not isinstance(entry, dict):
            raise ValueError(f"Turn {i + 1} is not a dict: {type(entry).__name__}")

        speaker = entry.get("speaker")
        if speaker not in ("voice1", "voice2"):
            raise ValueError(
                f"Turn {i + 1} has invalid speaker: {speaker!r}. "
                "Must be 'voice1' or 'voice2'."
            )

        if "text" not in entry or not entry["text"].strip():
            raise ValueError(f"Turn {i + 1} is missing or has empty 'text'.")
