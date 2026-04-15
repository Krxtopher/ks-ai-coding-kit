---
name: doc-convert
description: >
  Convert documents between formats using pandoc. Supports Markdown, Word (DOCX),
  HTML, LaTeX, PDF, and more. Ships with a styled Word reference template for
  polished Markdown-to-DOCX output. Use when the user asks to convert, export,
  or transform documents between formats.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: "1.0"
---

# Document Conversion with Pandoc

Convert documents between formats using [pandoc](https://pandoc.org/). This skill handles any conversion pandoc supports, with first-class support for producing polished Word documents from Markdown.

## Prerequisites

Pandoc must be installed on the system. Check with:

```bash
pandoc --version
```

If not installed, recommend:
- **macOS**: `brew install pandoc`
- **Ubuntu/Debian**: `sudo apt install pandoc`
- **Windows**: `choco install pandoc` or download from https://pandoc.org/installing.html

For PDF output, a LaTeX engine is also required (e.g., `brew install basictex` or `sudo apt install texlive`).

## Quick Reference

### Markdown → Word (recommended workflow)

This is the primary use case. Use the bundled reference template for styled output:

```bash
pandoc input.md -o output.docx \
  --reference-doc=SKILL_PATH/assets/reference.docx \
  --lua-filter=SKILL_PATH/assets/docx-polish.lua
```

Then fix list indentation (pandoc hardcodes deep nesting):

```bash
python SKILL_PATH/scripts/fix-list-indent.py output.docx
```

Replace `SKILL_PATH` with the actual path to this skill's directory. The reference template provides:
- **Aptos** font family (falls back to Calibri)
- Bold near-black headings with subtle bottom borders on H1/H2
- Cascadia Code for code blocks (falls back to Consolas)
- 1.2× line spacing for readability
- Styled block quotes, hyperlinks, and tables

The Lua filter adds:
- **Light gray background** on code blocks with an amber/orange left border accent
- **Gray character shading** on inline code

The post-processing script fixes:
- **Nested list indentation** reduced to ~1/3 of pandoc's default

### Other Common Conversions

```bash
# Markdown → HTML
pandoc input.md -o output.html --standalone

# Markdown → PDF (requires LaTeX)
pandoc input.md -o output.pdf

# Word → Markdown
pandoc input.docx -o output.md

# HTML → Markdown
pandoc input.html -o output.md

# Markdown → LaTeX
pandoc input.md -o output.tex

# Multiple inputs → single output
pandoc chapter1.md chapter2.md chapter3.md -o book.docx \
  --reference-doc=SKILL_PATH/assets/reference.docx \
  --lua-filter=SKILL_PATH/assets/docx-polish.lua
```

## Conversion Guidelines

### When converting TO Word (.docx)

1. **Always use the reference template and Lua filter** unless the user provides their own:
   ```bash
   pandoc input.md -o output.docx \
     --reference-doc=SKILL_PATH/assets/reference.docx \
     --lua-filter=SKILL_PATH/assets/docx-polish.lua
   python SKILL_PATH/scripts/fix-list-indent.py output.docx
   ```

2. **User-provided templates** take priority. If the user specifies a custom `.docx` template, use it instead:
   ```bash
   pandoc input.md -o output.docx --reference-doc=path/to/custom-template.docx
   ```

3. **Table of contents** — add `--toc` for longer documents:
   ```bash
   pandoc input.md -o output.docx \
     --reference-doc=SKILL_PATH/assets/reference.docx \
     --lua-filter=SKILL_PATH/assets/docx-polish.lua --toc
   python SKILL_PATH/scripts/fix-list-indent.py output.docx
   ```

4. **Metadata** — pandoc reads YAML front-matter from Markdown files for title, author, and date:
   ```markdown
   ---
   title: My Document
   author: Author Name
   date: 2025-01-15
   ---
   ```

### When converting TO HTML

- Use `--standalone` (or `-s`) to produce a complete HTML file with `<head>` and `<body>`.
- For styled HTML, add `--css=style.css` or use `--self-contained` to embed styles inline.

### When converting TO PDF

- Requires a LaTeX engine. If not available, suggest converting to DOCX first and exporting to PDF from Word.
- Use `--pdf-engine=xelatex` for better Unicode and font support.
- Custom margins: `--variable geometry:margin=1in`

### When converting FROM Word (.docx)

- Pandoc extracts text and basic formatting. Complex Word layouts may not convert perfectly.
- Use `--extract-media=./media` to save embedded images.

## Handling Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `pandoc: command not found` | Pandoc not installed | Install pandoc (see Prerequisites) |
| `Could not find reference.docx` | Wrong path to reference template | Verify the SKILL_PATH and that assets/reference.docx exists |
| `pdflatex not found` | No LaTeX engine for PDF output | Install LaTeX or convert to DOCX instead |
| `Could not convert image` | Unsupported image format | Convert images to PNG/JPEG first |

## Customizing the Reference Template

The bundled `assets/reference.docx` can be further customized:

1. Open it in Microsoft Word or LibreOffice Writer
2. Modify the styles (Heading 1, Heading 2, Normal, Source Code, etc.)
3. Save — pandoc reads styles from the template, not content

The `scripts/customize-reference.py` script can also regenerate the template from pandoc's defaults with the skill's style choices. It requires `python-docx`:

```bash
pip install python-docx
pandoc --print-default-data-file reference.docx > base.docx
python SKILL_PATH/scripts/customize-reference.py base.docx assets/reference.docx
```

## Advanced Options

Pandoc has extensive options. Some useful ones:

- `--wrap=none` — don't wrap long lines in text output
- `--columns=80` — wrap at 80 columns for text output
- `--shift-heading-level-by=-1` — promote all headings by one level
- `--strip-comments` — remove HTML comments from input
- `--lua-filter=filter.lua` — apply custom transformations
- `--metadata title="My Title"` — set metadata from the command line

For the full list, see `pandoc --help` or https://pandoc.org/MANUAL.html.
