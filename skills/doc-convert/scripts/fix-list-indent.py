#!/usr/bin/env python3
"""Post-process a pandoc-generated DOCX to reduce nested list indentation.

Pandoc hardcodes list indentation at ~720 twips per level, which produces
overly deep nesting. This script modifies the numbering definitions inside
the DOCX to use tighter indentation (~240 twips per level, roughly 1/3).

Requires: python-docx (pip install python-docx)

Usage:
    python fix-list-indent.py <file.docx>              # modifies in place
    python fix-list-indent.py <input.docx> <output.docx>
"""

import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

# OpenXML namespace
NSMAP = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
}

# Register namespaces so ET doesn't mangle them on write
for prefix, uri in NSMAP.items():
    ET.register_namespace(prefix, uri)

# Also register other common OOXML namespaces to preserve them
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
ET.register_namespace('mc', 'http://schemas.openxmlformats.org/markup-compatibility/2006')
ET.register_namespace('w14', 'http://schemas.microsoft.com/office/word/2010/wordml')
ET.register_namespace('w15', 'http://schemas.microsoft.com/office/word/2012/wordml')
ET.register_namespace('wps', 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape')

# Indentation config (in twips: 1440 = 1 inch, 720 = 0.5 inch)
BASE_LEFT = 360       # first level left indent
INCREMENT = 240       # additional indent per nesting level (~1/3 of pandoc default)
HANGING = 360         # hanging indent for bullet/number


def fix_numbering(numbering_xml: str) -> str:
    """Parse numbering.xml and adjust indentation on all abstractNum levels."""
    root = ET.fromstring(numbering_xml)

    for abstract_num in root.findall('.//w:abstractNum', NSMAP):
        for lvl in abstract_num.findall('w:lvl', NSMAP):
            ilvl = int(lvl.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ilvl',
                               lvl.get('w:ilvl', '0')))

            # Calculate new indentation
            left = BASE_LEFT + (ilvl * INCREMENT)

            # Find or create pPr
            pPr = lvl.find('w:pPr', NSMAP)
            if pPr is None:
                pPr = ET.SubElement(lvl, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')

            # Find or create ind
            ind = pPr.find('w:ind', NSMAP)
            if ind is None:
                ind = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ind')

            # Set the indentation values
            w_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
            ind.set(f'{{{w_ns}}}left', str(left))
            ind.set(f'{{{w_ns}}}hanging', str(HANGING))

    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def process_docx(input_path: Path, output_path: Path) -> None:
    """Open a DOCX, fix numbering indentation, save."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Copy input to temp location for in-place safety
        tmp_docx = tmp / "work.docx"
        shutil.copy2(input_path, tmp_docx)

        # Read the zip, modify numbering.xml, write back
        tmp_out = tmp / "output.docx"

        with zipfile.ZipFile(tmp_docx, 'r') as zin:
            with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)

                    if item.filename == 'word/numbering.xml':
                        # Fix the numbering definitions
                        fixed = fix_numbering(data.decode('utf-8'))
                        zout.writestr(item, fixed.encode('utf-8'))
                    else:
                        zout.writestr(item, data)

        # Move result to output
        shutil.copy2(tmp_out, output_path)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path

    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    process_docx(input_path, output_path)
    print(f"Fixed list indentation in {output_path}")


if __name__ == "__main__":
    main()
