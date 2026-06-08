#!/usr/bin/env python3
"""Play a random pre-generated acknowledgment phrase.

Picks a random MP3 from the phrases/ directory and plays it via afplay.
No network calls — just local file playback for minimal latency.
"""

import random
import subprocess
from pathlib import Path

PHRASES_DIR = Path(__file__).parent / "phrases"


def main() -> None:
    phrases = list(PHRASES_DIR.glob("*.mp3"))
    if not phrases:
        return

    chosen = random.choice(phrases)
    subprocess.Popen(
        ["afplay", str(chosen)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    main()
