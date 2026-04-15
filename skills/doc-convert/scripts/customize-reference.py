#!/usr/bin/env python3
"""Customize pandoc's default reference.docx with improved styling.

Modifies the Word styles in-place to produce a polished document inspired
by modern documentation sites — clean sans-serif body, bold dark headings,
code blocks with accent borders, and comfortable spacing.

Requires: python-docx (pip install python-docx)

Usage:
    python customize-reference.py <input.docx> <output.docx>
    python customize-reference.py <file.docx>  # modifies in place
"""

import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm, Emu, Inches
    from docx.enum.text import WD_LINE_SPACING
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("Error: python-docx is required. Install with: pip install python-docx")
    sys.exit(1)


# --- Color palette (warm, neutral, documentation-site aesthetic) ---
HEADING_COLOR = RGBColor(0x1A, 0x1A, 0x1A)   # Near-black
BODY_COLOR = RGBColor(0x2D, 0x2D, 0x2D)      # Dark charcoal
SUBTLE_COLOR = RGBColor(0x55, 0x55, 0x55)     # Medium gray
LINK_COLOR = RGBColor(0x2A, 0x7A, 0x8C)       # Muted teal
BORDER_COLOR = "C8510A"                         # Amber/orange (for code block accents)
CODE_BG = "F6F6F6"                              # Light gray background
QUOTE_BORDER = "D0D0D0"                         # Gray border for blockquotes
QUOTE_BG = "F9F9F9"                             # Very light gray for blockquotes

# --- Font stacks ---
BODY_FONT = "Sitka Text"
HEADING_FONT = "Sitka Text"
CODE_FONT = "Cascadia Code"


def set_font(style, name: str, size: Pt | None = None,
             color: RGBColor | None = None, bold: bool | None = None,
             italic: bool | None = None) -> None:
    """Apply font properties to a style."""
    font = style.font if hasattr(style, 'font') else style
    font.name = name
    if size is not None:
        font.size = size
    if color is not None:
        font.color.rgb = color
    if bold is not None:
        font.bold = bold
    if italic is not None:
        font.italic = italic


def set_paragraph_spacing(fmt, before: Pt | None = None, after: Pt | None = None,
                          line_spacing: float | None = None,
                          line_rule: int | None = None) -> None:
    """Set paragraph spacing properties."""
    if before is not None:
        fmt.space_before = before
    if after is not None:
        fmt.space_after = after
    if line_spacing is not None:
        fmt.line_spacing = line_spacing
    if line_rule is not None:
        fmt.line_spacing_rule = line_rule


def set_border_bottom(style, color_hex: str = "D0D0D0",
                      size: str = "4", space: str = "6") -> None:
    """Add a bottom border to a paragraph style (for heading separators)."""
    pPr = style.element.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        style.element.insert(0, pPr)

    pBdr = pPr.find(qn('w:pBdr'))
    if pBdr is None:
        pBdr = OxmlElement('w:pBdr')
        pPr.append(pBdr)

    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), size)
    bottom.set(qn('w:space'), space)
    bottom.set(qn('w:color'), color_hex)
    pBdr.append(bottom)


def set_border_left(style, color_hex: str, size: str = "18",
                    space: str = "8") -> None:
    """Add a left border accent to a paragraph style."""
    pPr = style.element.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        style.element.insert(0, pPr)

    pBdr = pPr.find(qn('w:pBdr'))
    if pBdr is None:
        pBdr = OxmlElement('w:pBdr')
        pPr.append(pBdr)

    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single')
    left.set(qn('w:sz'), size)
    left.set(qn('w:space'), space)
    left.set(qn('w:color'), color_hex)
    pBdr.append(left)


def set_shading(style, color_hex: str) -> None:
    """Add background shading to a style."""
    pPr = style.element.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        style.element.insert(0, pPr)

    # Remove existing shading
    existing = pPr.find(qn('w:shd'))
    if existing is not None:
        pPr.remove(existing)

    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    pPr.append(shd)


def customize(doc: Document) -> None:
    """Apply all style customizations to the document."""
    styles = doc.styles

    # --- Default / Normal paragraph ---
    normal = styles['Normal']
    set_font(normal, BODY_FONT, size=Pt(10.5), color=BODY_COLOR)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.2
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE

    # --- Headings ---
    # H1: Large, bold, near-black
    heading_configs = {
        'Heading 1': {
            'size': Pt(22), 'color': HEADING_COLOR, 'bold': True,
            'before': Pt(28), 'after': Pt(10), 'border_bottom': True,
        },
        'Heading 2': {
            'size': Pt(17), 'color': HEADING_COLOR, 'bold': True,
            'before': Pt(24), 'after': Pt(8), 'border_bottom': True,
        },
        'Heading 3': {
            'size': Pt(14), 'color': HEADING_COLOR, 'bold': True,
            'before': Pt(18), 'after': Pt(6), 'border_bottom': False,
        },
        'Heading 4': {
            'size': Pt(12), 'color': HEADING_COLOR, 'bold': True,
            'before': Pt(14), 'after': Pt(4), 'border_bottom': False,
        },
        'Heading 5': {
            'size': Pt(10.5), 'color': SUBTLE_COLOR, 'bold': True,
            'before': Pt(12), 'after': Pt(4), 'border_bottom': False,
        },
        'Heading 6': {
            'size': Pt(10.5), 'color': SUBTLE_COLOR, 'bold': True,
            'before': Pt(12), 'after': Pt(4), 'border_bottom': False,
        },
    }

    for name, cfg in heading_configs.items():
        try:
            style = styles[name]
        except KeyError:
            continue
        set_font(style, HEADING_FONT, size=cfg['size'], color=cfg['color'],
                 bold=cfg['bold'], italic=False)
        set_paragraph_spacing(style.paragraph_format,
                              before=cfg['before'], after=cfg['after'],
                              line_spacing=1.15,
                              line_rule=WD_LINE_SPACING.MULTIPLE)
        if cfg['border_bottom']:
            set_border_bottom(style, color_hex="E0E0E0")

    # --- Block quote — gray background with dark left border ---
    for quote_name in ['Block Text', 'Quote', 'Intense Quote']:
        try:
            style = styles[quote_name]
            set_font(style, BODY_FONT, size=Pt(10.5), color=BODY_COLOR,
                     italic=False)
            style.paragraph_format.left_indent = Cm(1.0)
            style.paragraph_format.right_indent = Cm(0.5)
            style.paragraph_format.space_before = Pt(8)
            style.paragraph_format.space_after = Pt(8)
            set_shading(style, QUOTE_BG)
            set_border_left(style, color_hex="4A4A4A", size="18", space="10")
        except KeyError:
            continue

    # --- Source Code / Verbatim — light bg with amber left border ---
    code_style_names = ['Source Code', 'Verbatim Char', 'Source Code Char']
    for name in code_style_names:
        try:
            style = styles[name]
            set_font(style, CODE_FONT, size=Pt(9.5))
        except KeyError:
            continue

    # Try to style the Source Code paragraph style with background + border
    try:
        source_code = styles['Source Code']
        set_shading(source_code, CODE_BG)
        set_border_left(source_code, color_hex=BORDER_COLOR, size="24", space="10")
        source_code.paragraph_format.space_before = Pt(8)
        source_code.paragraph_format.space_after = Pt(8)
        source_code.paragraph_format.line_spacing = 1.3
        source_code.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    except KeyError:
        pass

    # --- Table styles ---
    try:
        table_style = styles['Table']
        set_font(table_style, BODY_FONT, size=Pt(10))
    except KeyError:
        pass

    # --- Title and Subtitle ---
    try:
        title = styles['Title']
        set_font(title, HEADING_FONT, size=Pt(26), color=HEADING_COLOR, bold=True)
        title.paragraph_format.space_after = Pt(4)
    except KeyError:
        pass

    try:
        subtitle = styles['Subtitle']
        set_font(subtitle, HEADING_FONT, size=Pt(14), color=SUBTLE_COLOR,
                 italic=False, bold=False)
        subtitle.paragraph_format.space_after = Pt(16)
    except KeyError:
        pass

    # --- Hyperlinks ---
    try:
        hyperlink = styles['Hyperlink']
        hyperlink.font.color.rgb = LINK_COLOR
    except KeyError:
        pass

    # --- First Paragraph (used after headings sometimes) ---
    try:
        first_para = styles['First Paragraph']
        set_font(first_para, BODY_FONT, size=Pt(10.5), color=BODY_COLOR)
    except KeyError:
        pass

    # --- Compact / Body Text ---
    for name in ['Body Text', 'Compact']:
        try:
            style = styles[name]
            set_font(style, BODY_FONT, size=Pt(10.5), color=BODY_COLOR)
        except KeyError:
            continue


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path

    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    doc = Document(str(input_path))
    customize(doc)
    doc.save(str(output_path))
    print(f"Customized reference document saved to {output_path}")


if __name__ == "__main__":
    main()
