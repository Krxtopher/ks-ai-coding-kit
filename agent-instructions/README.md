# Agent Instructions

Reusable instruction files that guide AI coding agent behavior — coding standards, project context, workflows, and other standing directives.

## What Are These?

AI coding tools let you customize agent behavior through instruction files in your project. Each tool uses its own terminology and file conventions, but the underlying concept is the same: you write Markdown instructions, and the agent follows them.

| Tool | What They Call It | File / Location |
|------|-------------------|-----------------|
| Kiro | Steering files | `.kiro/steering/*.md` (also reads `AGENTS.md`) |
| Claude Code | Project instructions | `CLAUDE.md` (falls back to `AGENTS.md`) |
| Codex | Agent instructions | `AGENTS.md` in project root |
| GitHub Copilot | Custom instructions | `.github/copilot-instructions.md` (also reads `AGENTS.md`) |
| Cursor | Rules | `.cursor/rules/*.mdc` (also reads `AGENTS.md`) |

All of these tools read `AGENTS.md` at the repo root, making it the best single target for cross-tool instructions. The [installer](../install.py) appends instruction content to `AGENTS.md` in your project.

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

| File | Description |
|------|-------------|
| `documentation-standards.md` | Guidelines for when and how to update README.md and agent-facing docs |
