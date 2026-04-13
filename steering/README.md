# Steering Files

Reusable steering files that provide additional context and instructions to AI coding agents.

## What Are Steering Files?

Steering files are Markdown documents that guide AI agent behavior during coding sessions. They can enforce coding standards, provide project context, or define workflows.

## Compatibility

Steering files in this collection target **Kiro IDE**, which loads them from `.kiro/steering/` in your workspace.

Other tools have similar concepts (e.g., `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex) — see the `prompts/` directory for those.

## Installation

Copy any steering file into your workspace:

```bash
cp steering/<file>.md /path/to/your/project/.kiro/steering/
```

## Format

Each steering file is a standalone Markdown document. Files may include YAML front-matter for metadata:

```yaml
---
name: Python Conventions
description: PEP 8 style, type hints, and project structure standards
compatibility: Kiro IDE
tags: [python, style, conventions]
inclusion: auto
---
```

### Inclusion Modes (Kiro)

- `auto` (default) — Always included in agent context
- `fileMatch` — Included when a matching file is read (requires `fileMatchPattern`)
- `manual` — Included only when the user explicitly references it via `#` in chat

## Contents

*No standalone steering files yet. The `ai-memory` steering shim has been superseded by the ai-memory skill — see `skills/ai-memory/`.*
