"""Voice registry for the podcast generator (ElevenLabs).

Provides a catalog of popular ElevenLabs voices and a lookup function
that accepts either a registered name or a raw voice ID.

Usage:
    from voices import get_voice, list_voices

    voice = get_voice("Rachel")
    # {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "lang": "en-US", "gender": "Female"}

    voice = get_voice("JBFqnCBsd6RMkjVDRZzb")
    # {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "JBFqnCBsd6RMkjVDRZzb", "lang": "unknown", "gender": "unknown"}
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Voice catalog
#
# These are well-known ElevenLabs pre-made voices. Users can also pass any
# voice ID directly (including custom cloned voices).
# ---------------------------------------------------------------------------

VOICES: dict[str, dict[str, str]] = {
    # Popular pre-made voices
    "Rachel": {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "lang": "en-US", "gender": "Female"},
    "Drew": {"id": "29vD33N1CtxCmqQRPOHJ", "name": "Drew", "lang": "en-US", "gender": "Male"},
    "Clyde": {"id": "2EiwWnXFnvU5JabPnv8n", "name": "Clyde", "lang": "en-US", "gender": "Male"},
    "Paul": {"id": "5Q0t7uMcjvnagumLfvZi", "name": "Paul", "lang": "en-US", "gender": "Male"},
    "Domi": {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "lang": "en-US", "gender": "Female"},
    "Dave": {"id": "CYw3kZ02Hs0563khs1Fj", "name": "Dave", "lang": "en-US", "gender": "Male"},
    "Fin": {"id": "D38z5RcWu1voky8WS1ja", "name": "Fin", "lang": "en-US", "gender": "Male"},
    "Sarah": {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah", "lang": "en-US", "gender": "Female"},
    "Antoni": {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "lang": "en-US", "gender": "Male"},
    "Thomas": {"id": "GBv7mTt0atIp3Br8iCZE", "name": "Thomas", "lang": "en-US", "gender": "Male"},
    "Charlie": {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "lang": "en-US", "gender": "Male"},
    "George": {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "lang": "en-US", "gender": "Male"},
    "Emily": {"id": "LcfcDJNUP1GQjkzn1xUU", "name": "Emily", "lang": "en-US", "gender": "Female"},
    "Elli": {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "lang": "en-US", "gender": "Female"},
    "Callum": {"id": "N2lVS1w4EtoT3dr4eOWO", "name": "Callum", "lang": "en-US", "gender": "Male"},
    "Patrick": {"id": "ODq5zmih8GrVes37Dizd", "name": "Patrick", "lang": "en-US", "gender": "Male"},
    "Harry": {"id": "SOYHLrjzK2X1ezoPC6cr", "name": "Harry", "lang": "en-US", "gender": "Male"},
    "Liam": {"id": "TX3LPaxmHKxFdv7VOQHJ", "name": "Liam", "lang": "en-US", "gender": "Male"},
    "Dorothy": {"id": "ThT5KcBeYPX3keUQqHPh", "name": "Dorothy", "lang": "en-US", "gender": "Female"},
    "Josh": {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "lang": "en-US", "gender": "Male"},
    "Arnold": {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "lang": "en-US", "gender": "Male"},
    "Charlotte": {"id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "lang": "en-US", "gender": "Female"},
    "Alice": {"id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice", "lang": "en-US", "gender": "Female"},
    "Matilda": {"id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda", "lang": "en-US", "gender": "Female"},
    "James": {"id": "ZQe5CZNOzWyzPSCn5a3c", "name": "James", "lang": "en-US", "gender": "Male"},
    "Jeremy": {"id": "bVMeCyTHy58xNoL34h3p", "name": "Jeremy", "lang": "en-US", "gender": "Male"},
    "Michael": {"id": "flq6f7yk4E4fJM5XTYuZ", "name": "Michael", "lang": "en-US", "gender": "Male"},
    "Ethan": {"id": "g5CIjZEefAph4nQFvHAz", "name": "Ethan", "lang": "en-US", "gender": "Male"},
    "Chris": {"id": "iP95p4xoKVk53GoZ742B", "name": "Chris", "lang": "en-US", "gender": "Male"},
    "Brian": {"id": "nPczCjzI2devNBz1zQrb", "name": "Brian", "lang": "en-US", "gender": "Male"},
    "Daniel": {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "lang": "en-US", "gender": "Male"},
    "Lily": {"id": "pFZP5JQG7iQjIQuC4Bku", "name": "Lily", "lang": "en-US", "gender": "Female"},
    "Bill": {"id": "pqHfZKP75CvOlQylNhV4", "name": "Bill", "lang": "en-US", "gender": "Male"},
    "Jessica": {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica", "lang": "en-US", "gender": "Female"},
    "Eric": {"id": "cjVigY5qzO86Huf0OWal", "name": "Eric", "lang": "en-US", "gender": "Male"},
    "Nicole": {"id": "piTKgcLEGmPE4e6mEKli", "name": "Nicole", "lang": "en-US", "gender": "Female"},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_voice(name_or_id: str) -> dict[str, str]:
    """Look up a voice by name (case-insensitive) or accept a raw voice ID.

    If the input matches a registered voice name, returns that entry.
    Otherwise, treats it as a raw ElevenLabs voice ID and constructs a minimal dict.

    Args:
        name_or_id: A registered voice name (e.g. "Rachel") or a raw
                    ElevenLabs voice ID (e.g. "21m00Tcm4TlvDq8ikWAM").

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
