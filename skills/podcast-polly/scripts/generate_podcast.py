"""Podcast Generator — Turn any content into a two-voice audio podcast.

Orchestrates the full pipeline: script generation via Bedrock, audio
synthesis via Polly, and mixing with optional intro/outro music.

Supports three subcommands:
    generate  — Full pipeline (script + synthesize + mix)
    script    — Generate only the podcast script
    synthesize — Synthesize audio from an existing script

All outputs are saved to a timestamped folder under 'output/'.

Requirements:
    - Python 3.10+
    - boto3, pydub
    - ffmpeg installed (for audio mixing)
    - AWS credentials with Bedrock + Polly access

Usage:
    python generate_podcast.py generate --content-file summary.txt
    python generate_podcast.py script --content-file summary.txt --title "My Topic"
    python generate_podcast.py synthesize --run-dir output/20260712-1841_my-topic/
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import boto3

from mixer import assemble_podcast
from scriptgen import generate_script
from synthesize import get_polly_client, synthesize_segment, synthesize_segments
from voices import get_voice

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Assets: always relative to the skill installation directory
SKILL_ROOT = Path(__file__).parent.parent
ASSETS_DIR = SKILL_ROOT / "assets"
INTRO_SPEECH_FILE = ASSETS_DIR / "intro_speech.txt"
OUTRO_SPEECH_FILE = ASSETS_DIR / "outro_speech.txt"
DEFAULT_MUSIC_FILE = ASSETS_DIR / "music.mp3"

# Output: relative to user's CWD (where the script is invoked from)
OUTPUT_ROOT = Path.cwd() / "output"

# Timing constants for word budget calculation (must match mixer.py)
INTRO_MUSIC_DURATION_MS = 2000
DUCK_RAMP_MS = 1000
INTRO_RAMP_BACK_MS = 3000
INTRO_FADE_OUT_MS = 2000
OUTRO_FADE_IN_MS = 2500
OUTRO_FULL_VOLUME_MS = 3000
OUTRO_PAUSE_MS = 650

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(text: str, max_length: int = 40) -> str:
    """Convert text to a filesystem-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_length].rstrip("-")


def create_run_dir(title: str) -> Path:
    """Create and return a timestamped output directory."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    slug = slugify(title) or "podcast"
    dir_name = f"{timestamp}_{slug}"
    run_dir = OUTPUT_ROOT / dir_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_config(run_dir: Path, config: dict) -> Path:
    """Save the run configuration to the output folder."""
    config_path = run_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False, default=str))
    return config_path


def save_content(run_dir: Path, content: str) -> Path:
    """Save the content summary to the output folder."""
    content_path = run_dir / "content.txt"
    content_path.write_text(content, encoding="utf-8")
    return content_path


def load_config(run_dir: Path) -> dict:
    """Load the run configuration from an output folder."""
    config_path = run_dir / "config.json"
    if not config_path.exists():
        print(f"ERROR: No config.json found in {run_dir}", file=sys.stderr)
        sys.exit(1)
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_script(run_dir: Path) -> list[dict]:
    """Load the script from an output folder."""
    script_path = run_dir / "script.json"
    if not script_path.exists():
        print(f"ERROR: No script.json found in {run_dir}", file=sys.stderr)
        sys.exit(1)
    return json.loads(script_path.read_text(encoding="utf-8"))


def calculate_word_budget(duration: float, has_music: bool) -> int:
    """Calculate the word budget based on target duration and music presence."""
    if has_music:
        # Account for fixed intro/outro time
        intro_fixed_ms = (
            INTRO_MUSIC_DURATION_MS + DUCK_RAMP_MS +
            INTRO_RAMP_BACK_MS + DUCK_RAMP_MS + INTRO_FADE_OUT_MS
        )

        # Estimate outro speech duration
        outro_text = ""
        if OUTRO_SPEECH_FILE.exists():
            outro_text = OUTRO_SPEECH_FILE.read_text(encoding="utf-8").strip()
        outro_speech_words = len(outro_text.split()) if outro_text else 0
        outro_speech_ms = (outro_speech_words / 155) * 60000

        outro_fixed_ms = (
            OUTRO_FADE_IN_MS + 2000 + outro_speech_ms +
            DUCK_RAMP_MS + OUTRO_FULL_VOLUME_MS
        )
        fixed_ms = intro_fixed_ms + outro_fixed_ms + OUTRO_PAUSE_MS
        fixed_min = fixed_ms / 60000

        intro_speech_words = 25  # Approximate words in intro speech
        fixed_words = intro_speech_words + outro_speech_words

        effective_duration_min = max(0.5, duration - fixed_min)
        word_budget = int(effective_duration_min * 155) - fixed_words
    else:
        # No music — all duration goes to conversation
        word_budget = int(duration * 155)

    return max(100, word_budget)


def resolve_personality(value: str | None) -> str | None:
    """Resolve a personality argument: if it's a file path, read it; otherwise return as-is.

    Returns None if value is None (will use defaults from scriptgen).
    """
    if value is None:
        return None
    # Check if it looks like a file path
    path = Path(value)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8").strip()
    # Treat as inline text
    return value.strip()


def build_config_dict(args: argparse.Namespace, subcommand: str) -> dict:
    """Build a serializable config dict from parsed args."""
    config = {
        "subcommand": subcommand,
        "title": args.title,
        "duration": args.duration,
        "voice1": args.voice1,
        "voice2": args.voice2,
        "voice1_name": args.voice1_name,
        "voice2_name": args.voice2_name,
        "voice1_personality": resolve_personality(args.voice1_personality),
        "voice2_personality": resolve_personality(args.voice2_personality),
        "polly_endpoint": args.polly_endpoint,
        "profile": args.profile,
        "polly_profile": args.polly_profile,
        "model": args.model,
        "thinking": args.thinking,
        "music_volume": args.music_volume,
        "normalize": args.normalize,
        "timestamp": datetime.now().isoformat(),
    }
    intro_music = None if args.no_music else args.intro_music
    if intro_music:
        config["intro_music"] = str(intro_music)
    return config


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def run_script_generation(
    content_summary: str,
    config: dict,
    run_dir: Path,
) -> list[dict]:
    """Generate a podcast script and save it to the run directory."""
    voice1_voice = get_voice(config["voice1"])
    voice2_voice = get_voice(config["voice2"])
    voice1_name = config.get("voice1_name") or voice1_voice["name"]
    voice2_name = config.get("voice2_name") or voice2_voice["name"]
    if voice1_name.startswith("vc-"):
        voice1_name = "Alex"
    if voice2_name.startswith("vc-"):
        voice2_name = "Sam"

    has_music = bool(config.get("intro_music"))
    word_budget = calculate_word_budget(config["duration"], has_music)

    print(f"[1/1] Generating podcast script via Bedrock (~{word_budget} words)...", end=" ", flush=True)

    bedrock_session = boto3.Session(profile_name=config.get("profile"))
    try:
        script = generate_script(
            session=bedrock_session,
            content_summary=content_summary,
            voice1_name=voice1_name,
            voice2_name=voice2_name,
            title=config["title"],
            word_budget=word_budget,
            model_id=config.get("model"),
            use_thinking=config.get("thinking", False),
            voice1_personality=config.get("voice1_personality"),
            voice2_personality=config.get("voice2_personality"),
        )
        print("OK")
        print(f"      Generated {len(script)} turns")
    except Exception as e:
        print("FAILED")
        print(f"\n  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Print script preview
    print()
    print("  Script preview:")
    for i, entry in enumerate(script, 1):
        preview = entry["text"][:90] + ("..." if len(entry["text"]) > 90 else "")
        print(f"    {i:2}. [{entry['speaker']:6}] {preview}")
    print()

    # Save script
    script_path = run_dir / "script.json"
    script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False))
    print(f"      Script saved to: {script_path}")

    return script


def run_synthesis(
    script: list[dict],
    config: dict,
    run_dir: Path,
) -> None:
    """Synthesize audio from a script and mix the final podcast."""
    voice1_voice = get_voice(config["voice1"])
    voice2_voice = get_voice(config["voice2"])
    voice1_name = config.get("voice1_name") or voice1_voice["name"]
    voice2_name = config.get("voice2_name") or voice2_voice["name"]
    if voice1_name.startswith("vc-"):
        voice1_name = "Alex"
    if voice2_name.startswith("vc-"):
        voice2_name = "Sam"

    intro_music_path = Path(config["intro_music"]) if config.get("intro_music") else None
    has_music = intro_music_path and intro_music_path.exists()
    music_volume = config.get("music_volume", 100)

    # --- Synthesize segments ---
    print("[1/2] Synthesizing audio via Polly...")
    polly_profile = config.get("polly_profile") or config.get("profile")
    polly_session = boto3.Session(profile_name=polly_profile)

    synth_start = time.perf_counter()
    try:
        podcast_segments = synthesize_segments(
            session=polly_session,
            script=script,
            voice1_id=voice1_voice["id"],
            voice2_id=voice2_voice["id"],
            endpoint_url=config.get("polly_endpoint"),
        )
    except Exception as e:
        print("FAILED")
        print(f"\n  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    synth_time = time.perf_counter() - synth_start
    print(f"      Synthesis complete ({synth_time:.1f}s)")

    # --- Mix and assemble ---
    intro_speeches: list[bytes] | None = None
    outro_speech_bytes: bytes | None = None

    if has_music:
        print("[2/2] Mixing audio with intro/outro music...")
        polly_client = get_polly_client(polly_session, endpoint_url=config.get("polly_endpoint"))

        # Synthesize intro speech lines
        if INTRO_SPEECH_FILE.exists():
            intro_lines = INTRO_SPEECH_FILE.read_text(encoding="utf-8").strip().splitlines()
            format_vars = {
                "title": config["title"],
                "voice1_name": voice1_name,
                "voice2_name": voice2_name,
            }
            intro_speeches = []
            for idx, line_template in enumerate(intro_lines, 1):
                intro_text = line_template.strip().format(**format_vars)
                print(f"      Synthesizing intro line {idx}/{len(intro_lines)}...", end=" ", flush=True)
                intro_speeches.append(
                    synthesize_segment(polly_client, voice1_voice["id"], intro_text)
                )
                print("OK")

        # Synthesize outro speech
        if OUTRO_SPEECH_FILE.exists():
            outro_text = OUTRO_SPEECH_FILE.read_text(encoding="utf-8").strip()
            if outro_text:
                print("      Synthesizing outro...", end=" ", flush=True)
                outro_speech_bytes = synthesize_segment(
                    polly_client, voice1_voice["id"], outro_text
                )
                print("OK")
    else:
        print("[2/2] Assembling audio (no music)...")

    # Assemble final audio
    try:
        final_audio = assemble_podcast(
            segments=podcast_segments,
            intro_music_path=intro_music_path,
            intro_speeches=intro_speeches,
            outro_speech=outro_speech_bytes,
            music_volume_pct=music_volume,
        )
    except Exception as e:
        print("FAILED")
        print(f"\n  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Normalize if requested
    if config.get("normalize"):
        from mixer import normalize_audio
        print("      Normalizing audio (EBU R128, -14 LUFS)...", end=" ", flush=True)
        final_audio = normalize_audio(final_audio)
        print("OK")

    # Save output
    output_path = run_dir / "podcast.mp3"
    output_path.write_bytes(final_audio)

    # Calculate final duration
    from pydub import AudioSegment
    import io
    final_segment = AudioSegment.from_mp3(io.BytesIO(final_audio))
    duration_secs = len(final_segment) / 1000.0
    duration_min = int(duration_secs // 60)
    duration_sec = int(duration_secs % 60)

    print()
    print(f"    Podcast length:  {duration_min}:{duration_sec:02d}")
    print(f"    Audio size:      {len(final_audio):,} bytes")
    print(f"    Output file:     {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared across subcommands."""
    parser.add_argument(
        "--title",
        default="Podcast",
        help="Episode title (used in intro speech and folder name). Default: 'Podcast'",
    )
    parser.add_argument(
        "--voice1",
        default="Tiffany",
        help="Voice 1 (lead presenter): registered name or Polly voice ID. Default: Tiffany",
    )
    parser.add_argument(
        "--voice1-name",
        default=None,
        help="Display name for voice 1 in dialogue (default: inferred from --voice1)",
    )
    parser.add_argument(
        "--voice2",
        default="Stephen",
        help="Voice 2 (co-presenter): registered name or Polly voice ID. Default: Stephen",
    )
    parser.add_argument(
        "--voice2-name",
        default=None,
        help="Display name for voice 2 in dialogue (default: inferred from --voice2)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="Target podcast duration in minutes. Default: 2.0",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS profile for Bedrock (and Polly unless --polly-profile is set)",
    )
    parser.add_argument(
        "--polly-profile",
        default=None,
        help="Separate AWS profile for Polly synthesis",
    )
    parser.add_argument(
        "--polly-endpoint",
        default=None,
        help="Custom Polly endpoint URL (e.g. for beta/preview features). Omit for standard public endpoint.",
    )
    parser.add_argument(
        "--intro-music",
        type=Path,
        default=DEFAULT_MUSIC_FILE,
        help="Path to intro/outro music MP3 file (default: bundled music)",
    )
    parser.add_argument(
        "--no-music",
        action="store_true",
        help="Disable intro/outro music entirely",
    )
    parser.add_argument(
        "--music-volume",
        type=int,
        default=60,
        help="Music volume percentage (1-100). Default: 60",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the Bedrock model ID for script generation",
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="Enable adaptive thinking for script generation (slower, potentially better)",
    )
    parser.add_argument(
        "--voice1-personality",
        default=None,
        help="Personality description for voice 1 (inline text or path to .txt file). Default: src/voice1_personality.txt",
    )
    parser.add_argument(
        "--voice2-personality",
        default=None,
        help="Personality description for voice 2 (inline text or path to .txt file). Default: src/voice2_personality.txt",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging output",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize audio loudness to -14 LUFS (EBU R128 podcast standard)",
    )


def add_content_args(parser: argparse.ArgumentParser) -> None:
    """Add content input arguments."""
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument(
        "--content",
        help="Inline content summary text (for short summaries)",
    )
    content_group.add_argument(
        "--content-file",
        type=Path,
        help="Path to a text file containing the content summary",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a two-voice podcast from any content summary.",
        epilog=(
            "Examples:\n"
            "  python generate_podcast.py generate --content-file summary.txt\n"
            "  python generate_podcast.py script --content-file summary.txt --title 'My Topic'\n"
            "  python generate_podcast.py synthesize --run-dir output/20260712-1841_my-topic/"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Pipeline stage to run")

    # --- generate subcommand (full pipeline) ---
    gen_parser = subparsers.add_parser(
        "generate",
        help="Full pipeline: generate script, synthesize audio, and mix",
    )
    add_content_args(gen_parser)
    add_common_args(gen_parser)
    gen_parser.add_argument(
        "--script-only",
        action="store_true",
        help="Generate and print the script JSON without synthesizing audio (alias for 'script' subcommand)",
    )

    # --- script subcommand ---
    script_parser = subparsers.add_parser(
        "script",
        help="Generate only the podcast script (no audio synthesis)",
    )
    add_content_args(script_parser)
    add_common_args(script_parser)

    # --- synthesize subcommand ---
    synth_parser = subparsers.add_parser(
        "synthesize",
        help="Synthesize audio from an existing script in a run directory",
    )
    synth_parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Path to an existing run directory containing script.json and config.json",
    )
    # Allow overriding specific settings for re-synthesis
    synth_parser.add_argument(
        "--voice1",
        default=None,
        help="Override voice 1 from the saved config",
    )
    synth_parser.add_argument(
        "--voice2",
        default=None,
        help="Override voice 2 from the saved config",
    )
    synth_parser.add_argument(
        "--intro-music",
        type=Path,
        default=None,
        help="Override intro/outro music MP3 file",
    )
    synth_parser.add_argument(
        "--music-volume",
        type=int,
        default=None,
        help="Override music volume percentage (1-100)",
    )
    synth_parser.add_argument(
        "--polly-endpoint",
        default=None,
        help="Override Polly endpoint URL",
    )
    synth_parser.add_argument(
        "--profile",
        default=None,
        help="Override AWS profile",
    )
    synth_parser.add_argument(
        "--polly-profile",
        default=None,
        help="Override Polly AWS profile",
    )
    synth_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging output",
    )
    synth_parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize audio loudness to -14 LUFS (EBU R128 podcast standard)",
    )

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    return args


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> None:
    """Full pipeline: script generation + synthesis + mixing."""
    overall_start = time.perf_counter()

    # Load content
    content_summary = _load_content(args)

    # Resolve voice names for banner
    voice1_voice = get_voice(args.voice1)
    voice2_voice = get_voice(args.voice2)
    voice1_name = args.voice1_name or voice1_voice["name"]
    voice2_name = args.voice2_name or voice2_voice["name"]

    # Create output folder
    run_dir = create_run_dir(args.title)

    # Build and save config
    config = build_config_dict(args, "generate")
    save_config(run_dir, config)

    # Save content
    save_content(run_dir, content_summary)



    # Print banner
    _print_banner(args, run_dir, content_summary, voice1_name, voice1_voice, voice2_name, voice2_voice)

    # Step 1: Generate script
    script = run_script_generation(content_summary, config, run_dir)

    if args.script_only:
        print(json.dumps(script, indent=2, ensure_ascii=False))
        return

    # Step 2+3: Synthesize and mix
    run_synthesis(script, config, run_dir)

    overall_time = time.perf_counter() - overall_start

    # --- Done ---
    print()
    print("=" * 60)
    print("  Podcast generated successfully!")
    print("=" * 60)
    print(f"    Generation time: {overall_time:.1f}s")
    print(f"    Turns:           {len(script)}")
    print(f"    Run directory:   {run_dir}")
    print(f"\n    Play it with: afplay {run_dir / 'podcast.mp3'}")
    print()


def cmd_script(args: argparse.Namespace) -> None:
    """Generate only the podcast script."""
    # Load content
    content_summary = _load_content(args)

    # Resolve voice names for banner
    voice1_voice = get_voice(args.voice1)
    voice2_voice = get_voice(args.voice2)
    voice1_name = args.voice1_name or voice1_voice["name"]
    voice2_name = args.voice2_name or voice2_voice["name"]

    # Create output folder
    run_dir = create_run_dir(args.title)

    # Build and save config
    config = build_config_dict(args, "script")
    save_config(run_dir, config)

    # Save content
    save_content(run_dir, content_summary)

    # Print banner
    _print_banner(args, run_dir, content_summary, voice1_name, voice1_voice, voice2_name, voice2_voice)

    # Generate script
    run_script_generation(content_summary, config, run_dir)

    print()
    print("=" * 60)
    print("  Script generated successfully!")
    print("=" * 60)
    print(f"    Run directory: {run_dir}")
    print(f"    To synthesize: python scripts/generate_podcast.py synthesize --run-dir {run_dir}")
    print()


def cmd_synthesize(args: argparse.Namespace) -> None:
    """Synthesize audio from an existing run directory."""
    overall_start = time.perf_counter()
    run_dir = args.run_dir

    if not run_dir.exists():
        print(f"ERROR: Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Load saved config and script
    config = load_config(run_dir)
    script = load_script(run_dir)

    # Apply any overrides from CLI
    if args.voice1:
        config["voice1"] = args.voice1
    if args.voice2:
        config["voice2"] = args.voice2
    if args.intro_music:
        config["intro_music"] = str(args.intro_music)
    if args.music_volume is not None:
        config["music_volume"] = args.music_volume
    if args.polly_endpoint:
        config["polly_endpoint"] = args.polly_endpoint
    if args.profile:
        config["profile"] = args.profile
    if args.polly_profile:
        config["polly_profile"] = args.polly_profile
    if args.normalize:
        config["normalize"] = True

    # Save updated config
    save_config(run_dir, config)

    # Print banner
    voice1_voice = get_voice(config["voice1"])
    voice2_voice = get_voice(config["voice2"])
    voice1_name = config.get("voice1_name") or voice1_voice["name"]
    voice2_name = config.get("voice2_name") or voice2_voice["name"]

    print()
    print("=" * 60)
    print("  Podcast Synthesizer")
    print("=" * 60)
    print(f"    Run directory: {run_dir}")
    print(f"    Title:         {config['title']}")
    print(f"    Voice 1:       {voice1_name} ({voice1_voice['id']})")
    print(f"    Voice 2:       {voice2_name} ({voice2_voice['id']})")
    print(f"    Endpoint:      {config['endpoint']}")
    print(f"    Script turns:  {len(script)}")
    if config.get("intro_music"):
        print(f"    Music:         {config['intro_music']}")
        print(f"    Music volume:  {config.get('music_volume', 100)}%")
    print()

    # Synthesize and mix
    run_synthesis(script, config, run_dir)

    overall_time = time.perf_counter() - overall_start

    print()
    print("=" * 60)
    print("  Synthesis complete!")
    print("=" * 60)
    print(f"    Generation time: {overall_time:.1f}s")
    print(f"    Run directory:   {run_dir}")
    print(f"\n    Play it with: afplay {run_dir / 'podcast.mp3'}")
    print()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_content(args: argparse.Namespace) -> str:
    """Load and validate content from args."""
    if args.content_file:
        if not args.content_file.exists():
            print(f"ERROR: Content file not found: {args.content_file}", file=sys.stderr)
            sys.exit(1)
        content_summary = args.content_file.read_text(encoding="utf-8").strip()
    else:
        content_summary = args.content.strip()

    if not content_summary:
        print("ERROR: Content summary is empty.", file=sys.stderr)
        sys.exit(1)

    return content_summary


def _print_banner(
    args: argparse.Namespace,
    run_dir: Path,
    content_summary: str,
    voice1_name: str,
    voice1_voice: dict,
    voice2_name: str,
    voice2_voice: dict,
) -> None:
    """Print the informational banner at the start of a run."""
    print()
    print("=" * 60)
    print("  Podcast Generator")
    print("=" * 60)
    print(f"    Title:       {args.title}")
    print(f"    Target:      ~{args.duration:.1f} min")
    print(f"    Voice 1:     {voice1_name} ({voice1_voice['id']})")
    print(f"    Voice 2:     {voice2_name} ({voice2_voice['id']})")
    print(f"    Endpoint:    {args.endpoint}")
    print(f"    Run dir:     {run_dir}")
    if args.content_file:
        print(f"    Content:     {args.content_file} ({len(content_summary):,} chars)")
    else:
        print(f"    Content:     inline ({len(content_summary):,} chars)")
    if args.profile:
        print(f"    AWS Profile: {args.profile}")
    if args.polly_profile:
        print(f"    Polly Profile: {args.polly_profile}")
    if not args.no_music and args.intro_music:
        print(f"    Music:       {args.intro_music}")
        print(f"    Music vol:   {args.music_volume}%")
    if args.thinking:
        print(f"    Thinking:    enabled (adaptive)")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stderr,
    )

    if args.subcommand == "generate":
        cmd_generate(args)
    elif args.subcommand == "script":
        cmd_script(args)
    elif args.subcommand == "synthesize":
        cmd_synthesize(args)
    else:
        print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
