#!/usr/bin/env python3
"""Fix the theme fonts inside a DOCX reference template.

Pandoc's DOCX writer uses the document's theme fonts for headings,
ignoring the style-level font overrides. This script modifies the
theme XML inside the DOCX to set the desired major (heading) and
minor (body) fonts.

Usage:
    python fix-theme-fonts.py <file.docx>                          # modifies in place
    python fix-theme-fonts.py <file.docx> --major "Font" --minor "Font"
"""

import argparse
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Default fonts
DEFAULT_MAJOR = "Sitka Text"   # headings
DEFAULT_MINOR = "Sitka Text"   # body

# Theme namespace
NSMAP = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}

# Register all common OOXML namespaces to preserve them on write
OOXML_NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
}
for prefix, uri in OOXML_NS.items():
    ET.register_namespace(prefix, uri)


def fix_theme(theme_xml: str, major_font: str, minor_font: str) -> str:
    """Update the majorFont and minorFont in the theme XML."""
    root = ET.fromstring(theme_xml)

    # Find the font scheme element
    for font_scheme in root.iter(f'{{{NSMAP["a"]}}}fontScheme'):
        # Major font (headings)
        major = font_scheme.find(f'{{{NSMAP["a"]}}}majorFont')
        if major is not None:
            latin = major.find(f'{{{NSMAP["a"]}}}latin')
            if latin is not None:
                latin.set('typeface', major_font)

        # Minor font (body)
        minor = font_scheme.find(f'{{{NSMAP["a"]}}}minorFont')
        if minor is not None:
            latin = minor.find(f'{{{NSMAP["a"]}}}latin')
            if latin is not None:
                latin.set('typeface', minor_font)

    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def process_docx(input_path: Path, major_font: str, minor_font: str) -> None:
    """Open a DOCX, fix theme fonts, save in place."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tmp_docx = tmp / "work.docx"
        shutil.copy2(input_path, tmp_docx)

        tmp_out = tmp / "output.docx"
        theme_found = False

        with zipfile.ZipFile(tmp_docx, 'r') as zin:
            with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)

                    if 'theme' in item.filename.lower() and item.filename.endswith('.xml'):
                        fixed = fix_theme(data.decode('utf-8'), major_font, minor_font)
                        zout.writestr(item, fixed.encode('utf-8'))
                        theme_found = True
                    else:
                        zout.writestr(item, data)

        if not theme_found:
            print("Warning: No theme XML found in the DOCX.")

        shutil.copy2(tmp_out, input_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fix theme fonts inside a DOCX reference template."
    )
    parser.add_argument("input", type=Path, help="DOCX file to modify (in place)")
    parser.add_argument(
        "--major", type=str, default=DEFAULT_MAJOR,
        help=f"Major (heading) font (default: {DEFAULT_MAJOR})"
    )
    parser.add_argument(
        "--minor", type=str, default=DEFAULT_MINOR,
        help=f"Minor (body) font (default: {DEFAULT_MINOR})"
    )
    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    process_docx(input_path, args.major, args.minor)
    print(f"Theme fonts updated: major={args.major}, minor={args.minor}")


if __name__ == "__main__":
    main()
