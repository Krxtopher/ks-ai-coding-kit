#!/usr/bin/env python3
"""Describe an image using Amazon Bedrock vision models and extract technical metadata.

Usage:
    python describe.py <image_path> [--model MODEL_ID] [--prompt PROMPT] [--region REGION] [--profile PROFILE]

Outputs a combined report with:
  - Technical metadata (dimensions, file size, MIME type, bit depth, channels)
  - AI-generated description from a Bedrock vision model

Requires: boto3, Pillow
"""

import argparse
import json
import logging
import mimetypes
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install it with: pip install Pillow", file=sys.stderr)
    sys.exit(1)

try:
    import boto3
except ImportError:
    print("Error: boto3 is required. Install it with: pip install boto3", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "us.amazon.nova-2-lite-v1:0"
DEFAULT_REGION = "us-east-1"
DEFAULT_PROMPT = (
    "Describe this image in detail. Include the subject matter, composition, "
    "colors, text (if any), and any notable visual elements. Be thorough but concise."
)

# Mapping from PIL mode to human-readable channel info
MODE_INFO: dict[str, tuple[int, str]] = {
    "1": (1, "1-bit pixels, black and white"),
    "L": (1, "8-bit grayscale"),
    "P": (1, "8-bit palette-mapped"),
    "RGB": (3, "8-bit per channel, RGB"),
    "RGBA": (4, "8-bit per channel, RGBA"),
    "CMYK": (4, "8-bit per channel, CMYK"),
    "YCbCr": (3, "8-bit per channel, YCbCr"),
    "LAB": (3, "8-bit per channel, CIE LAB"),
    "HSV": (3, "8-bit per channel, HSV"),
    "I": (1, "32-bit signed integer pixels"),
    "F": (1, "32-bit floating point pixels"),
    "LA": (2, "8-bit grayscale with alpha"),
    "PA": (2, "8-bit palette-mapped with alpha"),
    "RGBa": (4, "8-bit per channel, premultiplied RGBA"),
    "I;16": (1, "16-bit unsigned integer pixels"),
    "I;16L": (1, "16-bit unsigned integer pixels, little-endian"),
    "I;16B": (1, "16-bit unsigned integer pixels, big-endian"),
}

# Bit depth per PIL mode
BIT_DEPTH: dict[str, int] = {
    "1": 1,
    "L": 8,
    "P": 8,
    "RGB": 24,
    "RGBA": 32,
    "CMYK": 32,
    "YCbCr": 24,
    "LAB": 24,
    "HSV": 24,
    "I": 32,
    "F": 32,
    "LA": 16,
    "PA": 16,
    "RGBa": 32,
    "I;16": 16,
    "I;16L": 16,
    "I;16B": 16,
}


def get_image_metadata(image_path: Path) -> dict:
    """Extract technical metadata from an image file."""
    file_size = image_path.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    with Image.open(image_path) as img:
        width, height = img.size
        mode = img.mode
        channels, channel_desc = MODE_INFO.get(mode, (len(img.getbands()), mode))
        bit_depth = BIT_DEPTH.get(mode, channels * 8)

    return {
        "file_name": image_path.name,
        "file_path": str(image_path.resolve()),
        "file_size_bytes": file_size,
        "file_size_human": _human_size(file_size),
        "mime_type": mime_type,
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "channels": channels,
        "channel_description": channel_desc,
    }


def describe_image(
    image_path: Path,
    model_id: str = DEFAULT_MODEL_ID,
    prompt: str = DEFAULT_PROMPT,
    region: str = DEFAULT_REGION,
    profile: str | None = None,
) -> str:
    """Send an image to a Bedrock vision model and return its description."""
    image_bytes = image_path.read_bytes()
    mime_type, _ = mimetypes.guess_type(str(image_path))

    # Map MIME type to Bedrock's expected format string
    format_map = {
        "image/jpeg": "jpeg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
    }
    image_format = format_map.get(mime_type, "jpeg")

    session_kwargs: dict = {}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    client = session.client("bedrock-runtime", region_name=region)

    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": image_format,
                            "source": {"bytes": image_bytes},
                        }
                    },
                    {"text": prompt},
                ],
            }
        ],
    )

    content_list = response["output"]["message"]["content"]
    text = next((item["text"] for item in content_list if "text" in item), None)
    return text or "(No text response from model)"


def _human_size(num_bytes: int) -> str:
    """Convert bytes to a human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{num_bytes} {unit}"
        num_bytes /= 1024  # type: ignore[assignment]
    return f"{num_bytes:.1f} TB"


def format_output(metadata: dict, description: str) -> str:
    """Format the combined metadata + description output."""
    lines = [
        "## Image Metadata",
        "",
        f"- **File**: {metadata['file_name']}",
        f"- **Path**: {metadata['file_path']}",
        f"- **Dimensions**: {metadata['width']} × {metadata['height']} px",
        f"- **File size**: {metadata['file_size_human']} ({metadata['file_size_bytes']:,} bytes)",
        f"- **MIME type**: {metadata['mime_type']}",
        f"- **Bit depth**: {metadata['bit_depth']}-bit",
        f"- **Channels**: {metadata['channels']} ({metadata['channel_description']})",
        "",
        "## AI Description",
        "",
        description,
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Describe an image using Bedrock vision models and extract metadata."
    )
    parser.add_argument("image_path", type=Path, help="Path to the image file")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help=f"Bedrock model ID (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt to send with the image (default: general description prompt)",
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help=f"AWS region (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS profile name (default: uses default credentials)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON instead of formatted Markdown",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    args = parse_args(argv)

    image_path: Path = args.image_path
    if not image_path.exists():
        logger.error("File not found: %s", image_path)
        sys.exit(1)
    if not image_path.is_file():
        logger.error("Not a file: %s", image_path)
        sys.exit(1)

    # Extract metadata (no network call needed)
    try:
        metadata = get_image_metadata(image_path)
    except Exception as e:
        logger.error("Failed to read image metadata: %s", e)
        sys.exit(1)

    # Get AI description from Bedrock
    try:
        description = describe_image(
            image_path,
            model_id=args.model,
            prompt=args.prompt,
            region=args.region,
            profile=args.profile,
        )
    except Exception as e:
        logger.error("Bedrock API call failed: %s", e)
        sys.exit(1)

    # Output
    if args.output_json:
        output = {**metadata, "description": description}
        print(json.dumps(output, indent=2))
    else:
        print(format_output(metadata, description))


if __name__ == "__main__":
    main()
