# Contributing

Thanks for your interest in contributing to KS AI Coding Kit! This guide covers everything you need to know to add new extensions or improve existing ones.

## What Is This Project?

This repo is a collection of reusable configuration and instruction files for AI coding assistants — tools like [Kiro](https://kiro.dev), [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex](https://openai.com/index/introducing-codex/), and [Cursor](https://www.cursor.com/) that embed AI agents directly into your development workflow.

Each of these tools lets you customize agent behavior through files in your project. The specifics vary by tool, but the general idea is the same: you write instructions or configuration, and the AI agent follows them. This repo packages those customizations into installable, shareable extensions.

If you're not familiar with these tools, the [README](README.md) has a background section and glossary that covers the key concepts (steering files, skills, hooks, prompts).

## Quick Start

1. Fork and clone the repo
2. Create a branch for your work
3. Add or modify an extension (see below for each type)
4. Add a catalog entry if you created something new
5. Update documentation if needed
6. Open a pull request

## Project Layout

```
ks-ai-coding-kit/
├── catalog.yaml       # Source of truth for all installable items
├── install.py         # CLI installer (Python 3.10+)
├── steering/          # Standalone steering files (.md)
├── skills/            # Agent Skills (each in its own subfolder)
├── hooks/             # Kiro hooks (.json)
├── prompts/           # System prompts grouped by tool
│   ├── claude-code/
│   └── codex/
└── docs/              # Project documentation
    ├── specs/         # Format specifications and reference docs
    └── IDEAS.md       # Future plans and ideas
```

## Adding a New Extension

Every new extension needs two things: the extension files themselves and a catalog entry.

### 1. Create the Extension

Pick the right type for what you're building. If you're unsure which type fits, check the [Concepts section in the README](README.md#concepts) for a quick overview.

**Skill** — A packaged capability that teaches the AI agent how to do something specific (e.g., manage persistent memory, run a code review workflow). Skills are multi-file packages under `skills/<skill-name>/` with a `SKILL.md` entry point. Follow the [Agent Skills specification](docs/specs/AgentSkillsSpecification.md) for the full format. At minimum:

```yaml
---
name: my-skill
description: What this skill does and when to use it.
---

Instructions for the agent go here.
```

The `name` field must be lowercase, use hyphens only, and match the directory name.

**Steering file** — A Markdown document that gives the AI agent standing instructions for a project (coding standards, architectural context, workflow rules). These are standalone files under `steering/`. Can include YAML front-matter for metadata:

```yaml
---
name: My Steering File
description: What guidance this provides
compatibility: Kiro IDE
tags: [relevant, tags]
inclusion: auto
---
```

**Hook** — An event-driven automation for Kiro IDE. Hooks fire when something happens in the IDE (a file is saved, a shell command is about to run, etc.) and trigger an action in response. They're JSON files under `hooks/` following the Kiro hook schema. See `hooks/README.md` for the full schema. Example:

```json
{
  "name": "My Hook",
  "version": "1.0.0",
  "description": "What this hook does",
  "when": {
    "type": "fileEdited",
    "patterns": ["*.py"]
  },
  "then": {
    "type": "runCommand",
    "command": "python -m py_compile ${file}"
  }
}
```

**Prompt** — A tool-specific system prompt or custom instruction file. Different AI coding tools look for these in different places (e.g., `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex). Place these under `prompts/<tool-name>/`.

### 2. Add a Catalog Entry

Every installable item must have an entry in `catalog.yaml`. Here's the structure:

```yaml
- name: my-extension
  type: skill | steering | hook | prompt
  source: path/to/source
  description: Clear, concise description
  tags: [relevant, tags]
  compatibility: [kiro, claude-code, codex, cursor]
  targets:
    kiro: .kiro/skills/my-extension
    claude-code: .claude/skills/my-extension
```

- `source` is the path relative to the repo root
- `targets` maps each compatible tool to its install destination (use `null` for incompatible tools)
- Only include tools in `compatibility` that you've actually tested or designed for

### 3. Include a Compatibility Note

Every item should declare which AI coding tools it supports, so users know what they can install it into. Use this format in file headers or front-matter:

```
Compatibility: Kiro IDE, Claude Code
```

Valid tool names: `Kiro IDE`, `Claude Code`, `Codex`, `GitHub Copilot`, `Cursor`, `Other`.

You don't need to support every tool. Many extensions only target one or two — that's fine. Just be accurate about what you've tested.

## Code Style

This project uses Python 3.10+ with no required external dependencies.

- Follow PEP 8
- Use type hints for function signatures
- Use `pathlib.Path` over `os.path`
- Use f-strings for formatting
- Keep functions focused — one responsibility each
- Use `logging` over `print()` for anything beyond CLI output

## Testing the Installer

After making changes, verify the installer still works:

```bash
# List all items (should include your new entry)
python install.py list

# Dry-run install to a temp directory
python install.py install <name> --dest /tmp/test-project --tool kiro --mode copy --dry-run
```

## Documentation

When your change adds, removes, or renames an extension — or changes how the installer or project structure works — update:

- **`README.md`** — Human-friendly, conversational tone
- **`AGENTS.md`** — Agent-facing, concise and direct

Both files should stay in sync about which extensions exist, but the writing style differs. Skip doc updates for purely internal changes that don't affect behavior or structure.

## Pull Request Guidelines

- Keep PRs focused on a single extension or change
- Include a clear description of what the extension does and which tools it targets
- If adding a skill, confirm it follows the [Agent Skills spec](docs/specs/AgentSkillsSpecification.md)
- Test your catalog entry with `install.py list` and a dry-run install

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
