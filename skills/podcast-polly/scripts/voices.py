"""Voice registry for the podcast generator.

Provides a catalog of Amazon Polly generative voices and a lookup function
that accepts either a registered name or a raw voice ID.

Usage:
    from voices import get_voice, list_voices

    voice = get_voice("Matthew")
    # {"id": "Matthew", "name": "Matthew", "lang": "en-US", "gender": "Male"}

    voice = get_voice("vc-56f8fbd479")
    # {"id": "vc-56f8fbd479", "name": "vc-56f8fbd479", "lang": "unknown", "gender": "unknown"}
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Voice catalog
# ---------------------------------------------------------------------------

VOICES: dict[str, dict[str, str]] = {
    # English (US)
    "Matthew": {"id": "Matthew", "name": "Matthew", "lang": "en-US", "gender": "Male"},
    "Danielle": {"id": "Danielle", "name": "Danielle", "lang": "en-US", "gender": "Female"},
    "Ruth": {"id": "Ruth", "name": "Ruth", "lang": "en-US", "gender": "Female"},
    "Kenneth": {"id": "Kenneth", "name": "Kenneth", "lang": "en-US", "gender": "Male"},
    "Tiffany": {"id": "Tiffany", "name": "Tiffany", "lang": "en-US", "gender": "Feminine"},
    # English (AU)
    "Olivia": {"id": "Olivia", "name": "Olivia", "lang": "en-AU", "gender": "Feminine"},
    # English (GB)
    "Amy": {"id": "Amy", "name": "Amy", "lang": "en-GB", "gender": "Feminine"},
    # English (IN)
    "Kiara": {"id": "Kiara", "name": "Kiara", "lang": "en-IN", "gender": "Feminine"},
    "Arjun": {"id": "Arjun", "name": "Arjun", "lang": "en-IN", "gender": "Masculine"},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_voice(name_or_id: str) -> dict[str, str]:
    """Look up a voice by name (case-insensitive) or accept a raw voice ID.

    If the input matches a registered voice name, returns that entry.
    Otherwise, treats it as a raw Polly voice ID and constructs a minimal dict.

    Args:
        name_or_id: A registered voice name (e.g. "Matthew") or a raw
                    Polly voice ID (e.g. "vc-56f8fbd479").

    Returns:
        A dict with keys: id, name, lang, gender.
    """
    key = next((k for k in VOICES if k.lower() == name_or_id.lower()), None)
    if key is not None:
        return VOICES[key]

    # Treat as raw voice ID
    return {"id": name_or_id, "name": name_or_id, "lang": "unknown", "gender": "unknown"}


def list_voices() -> list[dict[str, str]]:
    """Return all registered voices as a list of dicts."""
    return list(VOICES.values())
