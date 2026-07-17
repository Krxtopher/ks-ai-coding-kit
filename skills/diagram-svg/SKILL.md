---
name: diagram-svg
description: >
  Creates inline SVG diagrams directly in HTML, Markdown, or Jupyter notebooks
  with no external dependencies. Use this skill whenever the user asks for a
  diagram, flowchart, architecture diagram, relationship map, or visual
  explanation that should render natively in a document without external tools.
  Also use when the user wants finer typographic control than Mermaid provides —
  such as monospace code labels, italic function names, or custom colors. Trigger
  keywords: SVG diagram, inline diagram, architecture diagram, flow diagram,
  relationship diagram, HTML diagram, notebook diagram, no-dependency diagram.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: schultkr
  version: "1.0"
---

# SVG Diagram Skill

Creates publication-quality SVG diagrams that embed directly in documents. No
CLI tools, no npm packages, no browser rendering pipeline — just SVG markup that
works everywhere HTML is supported (Jupyter notebooks, GitHub markdown, HTML
pages, documentation sites).

## When to Use This vs Mermaid

| Choose this skill when… | Choose Mermaid when… |
|-------------------------|---------------------|
| You need typographic control (monospace, italic, mixed fonts) | A simple flowchart with default styling is sufficient |
| The diagram will embed inline in a notebook or markdown | You want auto-layout and don't care about precise positioning |
| No external tools should be required to render | Node.js and npx are available |
| You want custom colors, spacing, or annotations | The diagram needs to be editable in Mermaid Live Editor |
| The diagram has connector annotations that need precise placement | The relationships are simple enough that edge labels work fine |

---

## Workflow

### 1. Write the SVG to a Preview File

Write the SVG wrapped in a minimal HTML page to a temporary file prefixed with
`_` in the workspace root.

- File name pattern: `_<descriptive-name>.html`
- Example: `_deployment-flow.html`

```html
<!DOCTYPE html>
<html>
<head><title>Diagram Preview</title></head>
<body style="background: white; padding: 20px;">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 WIDTH HEIGHT"
     style="max-width: WIDTHpx; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
  <!-- diagram content -->
</svg>
</body>
</html>
```

### 2. Open for Preview

Open the HTML file in the user's default browser:

```bash
open _deployment-flow.html   # macOS
xdg-open _deployment-flow.html  # Linux
```

### 3. Iterate with Feedback

Keep the preview file in place and update it based on user feedback. Re-open
after each change (or the user can refresh the browser tab).

### 4. Embed in the Target Document

Once the user approves, embed the `<svg>` element directly into the target
document:

- **Jupyter notebook**: Place the SVG in a markdown cell's `source` array (each
  line as a JSON-escaped string)
- **Markdown/HTML**: Inline the `<svg>` element directly
- **Standalone image needed**: Keep the HTML file or use a screenshot

### 5. Clean Up

Delete the temporary `_*.html` preview file after successful embedding.

---

## Design Rules

These rules produce clear, readable diagrams. Follow them unless the user
explicitly overrides.

### Typography

| Content type | Font | Style |
|-------------|------|-------|
| Node titles / headings | System sans-serif (default) | `font-weight="bold"` |
| Descriptive text | System sans-serif (default) | Normal |
| Function / method names (things you call) | Monospace | `font-style="italic"` |
| Property / field names (things you read) | Monospace | Normal (upright) |
| Values and literals | Monospace | Normal |

The monospace font stack for code references:
```
font-family="SFMono-Regular, Menlo, Monaco, monospace"
```

The system sans-serif stack for everything else (set on the root `<svg>`):
```
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

### Connector Annotations

Annotations are text labels that describe what flows along a connector line.

- **Place annotations on vertical segments only.** Never place an annotation
  over a horizontal span of the connector it labels — this obscures the line
  path and makes it hard to trace where the connector goes.
- **Use a translucent background.** Every annotation that overlays a connector
  gets a background rect to ensure legibility:
  ```xml
  <rect x="..." y="..." width="..." height="..." rx="3" fill="rgba(255,255,255,0.85)"/>
  ```
- **Size the background to fit the text** with ~4px horizontal padding on each side.

### Arrows and Connectors

- Use orthogonal (right-angle) paths — not diagonal lines.
- Define a single arrowhead marker in `<defs>` and reuse it:
  ```xml
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 Z" fill="#666"/>
    </marker>
  </defs>
  ```
- Apply with `marker-end="url(#arrow)"` on path elements.
- When multiple connectors enter the same node, prefer symmetry — e.g., one
  from the left, one from the right — rather than stacking entries on one side.

### Spacing and Layout

- **ViewBox padding**: Always add 10–15px of padding beyond the lowest/rightmost
  element so nothing gets clipped.
- **Vertical spacing between node rows**: At least 50px clear between the bottom
  of one node and the top of the next to allow room for connector turns and
  annotations.
- **Node dimensions**: Minimum 200×60px for readability. Adjust width to fit
  text content.

### Color

Use a consistent, meaningful palette. Colors should encode semantic meaning
(e.g., all "source" nodes are one color, all "destination" nodes are another).
Suggested starting palette:

| Role | Fill | Text |
|------|------|------|
| Primary / entry point | `#232F3E` | white / `#FF9900` accent |
| Group / container | `#3F8624` | white / `#C5E8B7` secondary |
| Data entity | `#1B660F` | white / `#C5E8B7` secondary |
| Reference / external | `#527FFF` | white / `#D4DFFF` secondary |
| Storage / infrastructure | `#8C4FFF` | white / `#E0D4FF` secondary |
| Action / output | `#DD344C` | white |
| Connectors and arrows | `#666` | — |
| Annotation text | `#444` | — |

Override freely if the diagram's semantics call for different groupings, but stay
consistent within a single diagram.

### Nodes

- Rounded corners: `rx="6"` on node rects
- Smaller radius on annotation backgrounds: `rx="3"`
- Use `stroke` sparingly — either match `fill` or use a contrasting accent
  color for emphasis (like the orange stroke on the entry-point node)

---

## Embedding in Jupyter Notebooks

When embedding in a `.ipynb` file, the SVG goes into a markdown cell's `source`
array. Each line becomes a JSON-escaped string:

```json
{
  "cell_type": "markdown",
  "metadata": {},
  "source": [
    "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 780 580\" style=\"max-width: 680px; ...\">\n",
    "  <rect x=\"10\" y=\"10\" ... />\n",
    "  ...\n",
    "</svg>\n"
  ]
}
```

Use `max-width` on the SVG `style` attribute to control rendering width in the
notebook. The `viewBox` defines the coordinate space; `max-width` controls how
large it appears on screen.

---

## Example: Minimal Flow Diagram

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"
     style="max-width: 400px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
  <!-- Node A -->
  <rect x="100" y="10" width="200" height="60" rx="6" fill="#232F3E" stroke="#FF9900" stroke-width="2"/>
  <text x="200" y="35" text-anchor="middle" fill="white" font-size="14" font-weight="bold">Input</text>
  <text x="200" y="55" text-anchor="middle" fill="#FF9900" font-size="11"
        font-style="italic" font-family="SFMono-Regular, Menlo, Monaco, monospace">processData</text>

  <!-- Connector -->
  <path d="M 200 70 L 200 130" fill="none" stroke="#666" stroke-width="1.5" marker-end="url(#arrow)"/>
  <rect x="205" y="90" width="60" height="16" rx="3" fill="rgba(255,255,255,0.85)"/>
  <text x="235" y="102" text-anchor="middle" fill="#444" font-size="10"
        font-family="SFMono-Regular, Menlo, Monaco, monospace">payload</text>

  <!-- Node B -->
  <rect x="100" y="130" width="200" height="60" rx="6" fill="#3F8624" stroke="#3F8624" stroke-width="2"/>
  <text x="200" y="155" text-anchor="middle" fill="white" font-size="14" font-weight="bold">Output</text>
  <text x="200" y="175" text-anchor="middle" fill="#C5E8B7" font-size="11">result.json</text>

  <!-- Arrow marker -->
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M 0 0 L 8 4 L 0 8 Z" fill="#666"/>
    </marker>
  </defs>
</svg>
```

---

## Constraints

- **No external dependencies.** The SVG must render with zero tools installed —
  just a browser or notebook renderer.
- **Local preview only.** Use a local HTML file for iteration. Never use
  external rendering services.
- **Clean up on completion.** Delete the temporary `_*.html` file after the SVG
  is embedded in the target document.
- **Relative sizing.** Use `viewBox` for coordinate space and `max-width` for
  display size. Never use fixed `width`/`height` attributes on the `<svg>`
  element.
- **Accessible.** Include meaningful text content in the SVG (not just shapes)
  so screen readers can parse it.
