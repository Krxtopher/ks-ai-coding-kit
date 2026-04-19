# Agent Instructions

Reusable instruction files that guide AI coding agent behavior — coding standards, project context, workflows, and other standing directives.

## What Are These?

AI coding tools let you customize agent behavior through instruction files in your project. Each tool uses its own terminology and file conventions, but the underlying concept is the same: you write Markdown instructions, and the agent follows them.

| Tool | What They Call It | File / Location |
|------|-------------------|-----------------|
| Kiro | Steering files | `.kiro/steering/*.md` |
| Claude Code | Project instructions | `CLAUDE.md` in project root |
| Codex | Agent instructions | `AGENTS.md` in project root |
| GitHub Copilot | Custom instructions | `.github/copilot-instructions.md` |
| Cursor | Rules | `.cursorrules` or `.cursor/rules/*.md` |

The files in this directory are written to be tool-agnostic — the content works across agents. The [installer](../install.py) handles placing them in the right location for your tool.

## Format

Each instruction file is a standalone Markdown document. Files may include YAML front-matter for metadata:

```yaml
---
name: Python Conventions
description: PEP 8 style, type hints, and project structure standards
compatibility: Kiro IDE, Claude Code, Codex, Cursor
tags: [python, style, conventions]
---

Your instructions for the agent go here.
```

## Installation

Use the installer to add an instruction file to your project:

```bash
python install.py install <name> --dest /path/to/project --tool kiro
```

Or copy files manually to the appropriate location for your tool (see the table above).

## Contents

No agent instructions are currently available. All capabilities have been migrated to [skills](../skills/).
