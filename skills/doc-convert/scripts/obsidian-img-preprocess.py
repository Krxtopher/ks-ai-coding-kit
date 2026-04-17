#!/usr/bin/env python3
"""Preprocess Obsidian-style image embeds into standard Markdown.

Converts Obsidian's ![[image]] syntax to standard ![alt](path) syntax
so pandoc can process the images correctly.

Supported syntax:
    ![[image.png]]                  → ![image.png](image.png)
    ![[image.png|alt text]]         → ![alt text](image.png)
    ![[image.png|600]]              → ![image.png](image.png){ width=600px }
    ![[image.png|600x400]]          → ![image.png](image.png){ width=600px height=400px }
    ![[subfolder/image.png]]        → ![image.png](subfolder/image.png)
    ![[subfolder/image.png|caption]]→ ![caption](subfolder/image.png)

Usage:
    python obsidian-img-preprocess.py input.md > output.md
    python obsidian-img-preprocess.py input.md --image-dir attachments > output.md
    python obsidian-img-preprocess.py input.md --image-dir attachments -o output.md

Pipe directly to pandoc:
    python obsidian-img-preprocess.py input.md --image-dir attachments | \\
      pandoc -f markdown -o output.docx --reference-doc=reference.docx
"""

import re
import sys
from pathlib import Path

# Match ![[path]] or ![[path|text]]
OBSIDIAN_IMG_RE = re.compile(
    r'!\[\['
    r'([^\]|]+?)'       # group 1: file path
    r'(?:\|([^\]]*?))?'  # group 2: optional pipe-separated text (alt, width, or WxH)
    r'\]\]'
)

# Detect if the pipe text is a dimension spec
DIMENSION_RE = re.compile(r'^(\d+)(?:x(\d+))?$')

# Common image extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.tiff', '.ico'}


def is_image_path(path_str: str) -> bool:
    """Check if a path looks like an image file."""
    return Path(path_str.strip()).suffix.lower() in IMAGE_EXTENSIONS


def convert_obsidian_image(match: re.Match, image_dir: str | None = None) -> str:
    """Convert a single ![[...]] match to standard Markdown image syntax."""
    file_path = match.group(1).strip()
    pipe_text = match.group(2)

    # Only convert if it looks like an image
    if not is_image_path(file_path):
        return match.group(0)  # leave non-image embeds unchanged

    # Build the image source path
    filename = Path(file_path).name
    if image_dir:
        src = f"{image_dir}/{file_path}" if '/' in file_path else f"{image_dir}/{file_path}"
    else:
        src = file_path

    # Determine alt text and optional dimensions
    alt = filename
    attrs = ""

    if pipe_text is not None:
        pipe_text = pipe_text.strip()
        dim_match = DIMENSION_RE.match(pipe_text)
        if dim_match:
            # It's a dimension spec
            width = dim_match.group(1)
            height = dim_match.group(2)
            if height:
                attrs = f'{{ width={width}px height={height}px }}'
            else:
                attrs = f'{{ width={width}px }}'
        else:
            # It's alt text
            alt = pipe_text

    result = f'![{alt}]({src})'
    if attrs:
        result += attrs

    return result


def preprocess(text: str, image_dir: str | None = None) -> str:
    """Replace all Obsidian image embeds in the text."""
    return OBSIDIAN_IMG_RE.sub(
        lambda m: convert_obsidian_image(m, image_dir),
        text
    )


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0 if sys.argv[1:] == ['--help'] else 1)

    input_path = Path(sys.argv[1])
    image_dir: str | None = None
    output_path: Path | None = None

    # Parse args
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--image-dir' and i + 1 < len(args):
            image_dir = args[i + 1].rstrip('/')
            i += 2
        elif args[i] == '-o' and i + 1 < len(args):
            output_path = Path(args[i + 1])
            i += 2
        else:
            i += 1

    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    text = input_path.read_text(encoding='utf-8')
    result = preprocess(text, image_dir)

    if output_path:
        output_path.write_text(result, encoding='utf-8')
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
