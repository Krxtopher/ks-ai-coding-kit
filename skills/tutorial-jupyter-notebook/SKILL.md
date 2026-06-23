---
name: tutorial-jupyter-notebook
description: >
  Guide for creating high-quality educational Jupyter Notebooks that teach workflows,
  patterns, and technical concepts. Use this skill whenever the user asks to create a
  notebook, tutorial, walkthrough, demo, or educational material in .ipynb format.
  Also use when converting scripts or workflows into notebook form, or when the user
  mentions wanting to teach or explain something via a notebook.
metadata:
  author: schultkr
  version: "1.0"
---

# Tutorial Notebook Skill

This skill guides the creation of educational Jupyter Notebooks that are readable,
reproducible, and pedagogically effective. It synthesizes best practices from the
academic literature on computational notebooks in education.

## Core Philosophy

A tutorial notebook is not a script with comments — it is a **narrative document**
that happens to contain executable code. The reader should be able to understand the
content by reading it top-to-bottom, even without executing cells. The code cells
serve as concrete demonstrations woven into that narrative.

The guiding principle: **explain first, show second, interpret third.**

---

## Notebook Structure

### Overall Layout

```
1. Title & Metadata (H1)
   - One-sentence summary of what the reader will learn
   - Prerequisites (knowledge, packages, credentials)
   - Estimated time to complete

2. Overview / Motivation (H2)
   - Why this workflow matters
   - What problem it solves
   - Architecture diagram or visual (if applicable)

3. Setup (H2)
   - Imports
   - Configuration (region, bucket, model ID, etc.)
   - Helper function imports from companion .py modules

4. Main Content — Numbered Workflow Steps (H2 each)
   - Each major step gets its own H2 section
   - Markdown intro → code cell → markdown interpretation of output

5. Results & Discussion (H2)
   - Summarize what was accomplished
   - Key takeaways

6. Next Steps / Exercises (H2)
   - Suggest things the reader can try
   - Link to related notebooks or docs

7. Cleanup (H2, if applicable)
   - Delete resources, close connections
```

### Section Sequencing

Use a **Win-day-one** approach for complex workflows:
- Show the end-to-end result concisely first (a "TL;DR" cell or summary section)
- Then break down each step methodically

For multi-notebook tutorials, use a numbered naming convention:
```
00-overview.ipynb        (shows full workflow, links to sub-notebooks)
01-data-preparation.ipynb
02-training.ipynb
03-evaluation.ipynb
```

---

## Writing Guidelines

### Text-to-Code Ratio

Target a **3:1 ratio** of markdown text to code. Every code cell should be:
- **Preceded** by a markdown cell explaining what the code does and why
- **Followed** by a markdown cell interpreting the output (when output is non-trivial)

### Markdown Cells

- Use **H1** for the notebook title only (one per notebook)
- Use **H2** for major sections (workflow steps)
- Use **H3** for subsections within a step
- Use **bold** for key terms on first use
- Use blockquotes (`>`) for important notes, caveats, or tips:

```markdown
> 💡 **Tip:** If training takes too long, reduce `max_steps` for a quick test run.

> ⚠️ **Note:** This operation is not idempotent — running it twice will create
> duplicate resources.
```

- Include a **Table of Contents** at the top for notebooks with 5+ sections
- Add horizontal rules (`---`) between major conceptual shifts

### Code Cells

- **One logical operation per cell.** If you're tempted to add a comment saying
  "Now we do X" in the middle of a cell, that's a sign to split.
- **Keep cells under 15 lines.** Extract longer logic into functions.
- **Name variables for clarity over brevity.** `training_data_path` not `tdp`.
- **Use f-strings** to present computed values with context and units.
- **Include inline comments** only for non-obvious operations. The surrounding
  markdown carries the main narrative.
- **Format code consistently** (Black style: 88 char line width).
- **Avoid magic numbers.** Define constants in a configuration cell at the top.
- **Show output.** Save notebooks with cell outputs rendered so readers can follow
  along without executing.

### Interpreting Results

Never leave a code cell's output uninterpreted. After any cell that produces
meaningful output (a number, a DataFrame, a plot, an API response), add a markdown
cell that:
1. States what the output means in plain language
2. Highlights anything notable or unexpected
3. Connects it to the next step

Bad:
```python
print(metrics["accuracy"])
# 0.847
```

Good:
```python
print(f"Model accuracy on held-out test set: {metrics['accuracy']:.1%}")
```
Followed by a markdown cell: "An accuracy of 84.7% on the held-out test set exceeds
our 80% target. This suggests the model generalizes well beyond the training
distribution."

---

## Code Organization

### Companion Modules

Tuck helper functions, utility code, and boilerplate into companion `.py` files
that live alongside the notebook. The notebook's code should focus on the pedagogical
flow — not on utility plumbing.

```
my-tutorial/
├── 01-training.ipynb
├── helpers.py          # Utility functions imported by the notebook
├── config.py           # Shared configuration
└── requirements.txt    # Pinned dependencies
```

In the notebook:
```python
from helpers import format_results, upload_to_s3
```

This keeps the notebook focused while still providing the reader access to the
full implementation if they want to inspect the helper module.

### When NOT to Extract

Keep code inline when it IS the lesson — when seeing the implementation is the point.
Only extract code that's incidental to the tutorial's learning objectives.

---

## Reproducibility Requirements

These are non-negotiable for any tutorial notebook:

1. **"Restart and Run All" must succeed.** Test this before sharing. If cells
   depend on execution-order tricks or manual intervention, the notebook is broken.

2. **Pin dependencies.** Provide a `requirements.txt` or `environment.yml` with
   exact versions alongside the notebook.

3. **Use relative paths.** Never hardcode absolute paths. Use `pathlib.Path` and
   keep data files in a predictable relative location.

4. **Document data provenance.** If the notebook uses data, explain where it comes
   from, how to obtain it, and what date/version was used. Prefer download scripts
   over bundling large files.

5. **Declare all prerequisites upfront.** If the notebook requires AWS credentials,
   a specific Python version, or a running service — say so in the first cell.

6. **Idempotent operations.** Where possible, design cells so running them twice
   doesn't cause errors or duplicate resources. Where not possible, warn the reader.

---

## Visual Design

### Diagrams and Visuals

- Include an **architecture diagram** or **workflow visual** early in the notebook
  to orient readers before diving into code. Even a simple ASCII diagram helps.
- Use **matplotlib/seaborn** for data visualizations with clear titles, axis labels,
  and legends.
- Keep DataFrame displays to `.head()` or `.sample(5)` — never dump hundreds of rows.

### Callout Patterns

Use these consistently throughout:

```markdown
> 💡 **Tip:** Optional enhancement or efficiency suggestion

> ⚠️ **Warning:** Something that could cause errors or unexpected behavior

> 📝 **Note:** Important context or clarification

> 🔑 **Key Concept:** A core idea the reader should remember
```

---

## Pedagogical Patterns

Choose the pattern that fits your tutorial's goal:

| Pattern | Use When |
|---------|----------|
| **Shift-Enter walkthrough** | Reader follows along step-by-step, executing sequentially |
| **Tweak-and-explore** | You want readers to experiment with parameters |
| **Fill-in-the-blanks** | Workshop-style, scaffolded with deliberate gaps |
| **Top-down sequence** | Show what a tool does before explaining how it works |
| **The API is the lesson** | Learning the SDK interface IS the objective |

For AWS workflow tutorials, **Shift-Enter walkthrough** combined with
**Tweak-and-explore** (exposing key parameters in a config cell) works best.

---

## AWS-Specific Conventions

When the tutorial involves AWS services:

- Put all AWS configuration (region, bucket, model ID, role ARN) in a single
  early "Configuration" cell with clear variable names
- Use `boto3` sessions explicitly rather than relying on ambient defaults
- Include IAM permission requirements in the Prerequisites section
- Add estimated cost warnings for any billable operations
- Show how to clean up resources at the end
- Use `%%time` or timing wrappers for long-running API calls so readers know
  what to expect

---

## Anti-Patterns to Avoid

- ❌ Monolithic code cells with 50+ lines
- ❌ Bare numeric output without interpretation
- ❌ Importing everything at the top with no explanation of what each import does
- ❌ Using `print()` when a formatted f-string or display would be clearer
- ❌ Leaving debugging output or exploratory cells in the final version
- ❌ Execution counters in high double/triple digits (sign of non-linear execution)
- ❌ Assuming the reader knows acronyms or jargon without defining them
- ❌ Cells that silently mutate state without visible output
- ❌ Hardcoded credentials or account IDs in code cells (use config cells or env vars)

---

## Checklist Before Sharing

Before considering a tutorial notebook complete:

- [ ] Title clearly states what the reader will learn
- [ ] Prerequisites are listed (packages, credentials, knowledge)
- [ ] "Restart and Run All" executes without errors
- [ ] All outputs are saved and visible in the rendered notebook
- [ ] Every code cell has a preceding markdown explanation
- [ ] Every meaningful output has a following markdown interpretation
- [ ] No cell exceeds ~15 lines of code
- [ ] Configuration is centralized in an early cell
- [ ] Helper/utility code is extracted to companion modules
- [ ] Dependencies are pinned in a requirements file
- [ ] Data sources are documented with provenance
- [ ] Cleanup instructions are included (if resources were created)
- [ ] Callouts highlight tips, warnings, and key concepts
- [ ] The notebook reads coherently as a top-to-bottom narrative
