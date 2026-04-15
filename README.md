# KS AI Coding Kit

A curated collection of reusable extensions for AI coding tools — steering files, agent skills, hooks, and system prompts.

## Background

A growing number of code editors and IDEs now ship with built-in AI agents that can read your project, suggest changes, and run commands on your behalf. Each tool has its own way of letting you customize agent behavior — configuration files, instruction documents, event-driven hooks, and so on.

This repo collects reusable extensions that work across several of these tools:

| Tool | What It Is |
|------|-----------|
| [Kiro](https://kiro.dev) | An AI-native IDE from Amazon that supports steering files, agent skills, and event-driven hooks |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Anthropic's CLI coding agent, configured via `CLAUDE.md` and skill packages |
| [Codex](https://openai.com/index/introducing-codex/) | OpenAI's coding agent, guided by `AGENTS.md` and similar instruction files |
| [Cursor](https://www.cursor.com/) | An AI-augmented code editor that supports custom rules and skill packages |

You don't need to use all of these tools. Each extension declares which tools it's compatible with, and the installer handles putting files in the right place.

## Concepts

If you're new to AI coding assistants, here's a quick glossary of the extension types in this repo:

- **Steering files** — Markdown documents that give the AI agent standing instructions (coding standards, project context, workflows). Think of them as a persistent system prompt scoped to your project.
- **Skills** — Multi-file packages that teach the agent a specific capability (e.g., managing a memory system). A skill includes a `SKILL.md` entry point with metadata and instructions, plus optional scripts and reference docs.
- **Hooks** — Event-driven automations for Kiro IDE. A hook listens for an IDE event (file saved, command about to run, etc.) and triggers an action — either a shell command or a follow-up prompt to the agent.
- **Prompts** — Tool-specific system prompts or custom instruction files (e.g., a `CLAUDE.md` for Claude Code).

## What's Here

| Directory | What It Contains | Target Tools |
|-----------|-----------------|--------------|
| `steering/` | Reusable steering/instruction files | Kiro IDE |
| `skills/` | Agent Skills (multi-file skill packages) | Kiro IDE, Claude Code, Codex, Cursor |
| `hooks/` | Agent hooks triggered by IDE events | Kiro IDE |
| `prompts/` | System prompts and custom instructions | Claude Code, Codex, others |

## Available Extensions

### Skills

| Directory | Description |
|-----------|-------------|
| [`ai-memory`](skills/ai-memory/SKILL.md) | Persistent AI memory system with project-scoped and user-scoped memory files for retaining context across conversations. Works with Kiro, Claude Code, Codex, and Cursor. |
| [`doc-convert`](skills/doc-convert/SKILL.md) | Convert documents between formats using pandoc. Ships with a styled Word reference template for polished Markdown-to-DOCX output. Works with Kiro, Claude Code, Codex, and Cursor. |

### Steering Files

| File | Description |
|------|-------------|

### Hooks

| File | Description |
|------|-------------|
| [`shell-command-explainer.kiro.hook`](hooks/shell-command-explainer.kiro.hook) | Explains shell commands before execution and provides safety/trust analysis for auto-approval decisions |

## Getting Started

Browse the directories above and check each category's README for format details and installation instructions.

> [!IMPORTANT]
> Each item includes a **Compatibility** note indicating which AI coding tools it works with. Check this before installing.

## Installation

Use the included installer to browse and install extensions into your project.

### Browsing the Catalog

```bash
# List all available extensions
python install.py list

# Filter by tag, type, or tool
python install.py list --tag safety
python install.py list --type hook
python install.py list --tool kiro
```

### Interactive Install (Recommended)

The simplest way to install is to provide just the item name and destination. The installer walks you through the rest:

```bash
python install.py install ai-memory --dest ~/my-project
```

```
Which tool are you installing 'ai-memory' for?
  1) kiro
  2) claude-code
  3) codex
  4) cursor
Enter choice: 1
How should the extension be installed?
  1) copy
  2) symlink (see warning below)

⚠ Symlink mode is not supported by Kiro (skills installed as symlinks
won't be discovered). Compatibility with other tools is unverified —
use symlinks at your own risk. Prefer 'copy' mode unless you are
actively developing this extension.
Enter choice: 1
✓ Installed 'ai-memory' (copy) → /Users/you/my-project/.kiro/skills/ai-memory
  ↳ Injected steering into /Users/you/my-project/AGENTS.md
```

If an item only supports one tool, that step is skipped automatically:

```
Only one compatible tool: kiro
How should the extension be installed?
  1) copy
  2) symlink (see warning below)

⚠ Symlink mode is NOT supported by kiro. Extensions installed as
symlinks will not be discovered. Prefer 'copy' mode unless you are
actively developing this extension.
Enter choice: 2
✓ Installed 'shell-command-explainer' (symlink) → /Users/you/my-project/.kiro/hooks/shell-command-explainer.kiro.hook
```

Uninstall works the same way — omit `--tool` and you'll be prompted:

```bash
python install.py uninstall ai-memory --dest ~/my-project
```

### Advanced Usage with Flags

For scripting or CI, you can skip the prompts entirely by passing `--tool` and `--mode` directly:

```bash
# Install as a copy (recommended)
python install.py install ai-memory --dest /path/to/project --tool kiro --mode copy

# Install as a symlink (see warning below)
python install.py install ai-memory --dest /path/to/project --tool claude-code --mode symlink

# Preview what would happen without making changes
python install.py install ai-memory --dest /path/to/project --tool kiro --mode copy --dry-run

# Uninstall
python install.py uninstall ai-memory --dest /path/to/project --tool kiro
```

> [!WARNING]
> **Symlink mode caveat:** Symlink installs are **known not to work with Kiro** — skills installed as symlinks won't be discovered by the IDE. Compatibility with other tools (Claude Code, Codex, Cursor) is unverified. Prefer `copy` mode for all normal use. Symlinks are only useful if you're actively developing an extension in this repo and want live edits reflected without re-copying — but even then, consider using `python install.py sync` instead.

### Syncing Updates

When you improve an extension in this repo, you can push the changes to all workspaces where it's installed using the `sync` command:

```bash
# Re-copy all installed items to their registered destinations
python install.py sync

# Sync just one item
python install.py sync ai-memory

# Preview what would be synced
python install.py sync --dry-run
```

The installer tracks where each item was installed in a local manifest file (`.install-manifest.json`, gitignored). `install` adds entries there, `uninstall` removes the corresponding entry when cleanup succeeds, and `sync` reads the manifest to know what to update.

This means your workflow for making improvements is:

1. Edit the extension in this repo
2. Run `python install.py sync`
3. All workspaces get the updated files

> [!TIP]
> Use `sync` instead of symlinks to keep a single source of truth. You get the same "edit once, update everywhere" benefit without the tool compatibility issues that symlinks introduce.

### Steering Injection

> [!NOTE]
> Some extensions (like `ai-memory`) need to be activated at the start of every conversation. The installer handles this automatically by appending a one-liner to your project's root steering file:

- **AGENTS.md** for Kiro, Codex, Cursor, and other tools that support the [AGENTS.md](https://agents.md) standard
- **CLAUDE.md** for Claude Code

The injected text is wrapped in HTML comment markers so it can be cleanly removed on uninstall.

### Manual Installation

You can also copy files directly:

- **Kiro steering** → `.kiro/steering/` in your workspace
- **Kiro skills** → `.kiro/skills/` in your workspace
- **Kiro hooks** → `.kiro/hooks/` in your workspace
- **Claude Code prompts** → `CLAUDE.md` in your project root
- **Codex prompts** → `AGENTS.md` or `codex.md` in your project root

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. The short version: add your extension files, create a catalog entry in `catalog.yaml`, include a Compatibility note, and open a PR.

## License

See [LICENSE](LICENSE) for details.
