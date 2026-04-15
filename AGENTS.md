# AGENTS.md

Agent-facing documentation for the `ks-ai-coding-kit` repository.

## Project Structure

```
ks-ai-coding-kit/
├── catalog.yaml       # Source of truth for all installable items
├── install.py         # CLI installer (Python 3.10+, no required deps)
├── steering/          # Reusable steering files (single .md files)
├── skills/            # Kiro Agent Skills (each in its own subfolder with SKILL.md)
├── hooks/             # Kiro hooks (.json files)
├── prompts/           # System prompts grouped by target tool
│   ├── claude-code/
│   └── codex/
└── docs/              # Project documentation
    ├── specs/         # Format specifications and reference docs for building new items
    └── IDEAS.md       # Future plans and ideas
```

## Conventions

- **Catalog** (`catalog.yaml`) is the source of truth for all installable items. Each entry defines name, type, source path, description, tags, compatibility, and per-tool install targets.
- **Installer** (`install.py`) reads the catalog and copies or symlinks items to the correct location. Supports `list`, `install`, `uninstall`, `sync`, `--dry-run`, `--tool`, `--mode copy|symlink`, `--tag`, `--type`. Prompts interactively for `--tool` and `--mode` when omitted. No dependencies beyond Python 3.10+ (PyYAML optional).
- **Install manifest** (`.install-manifest.json`) is a local, gitignored registry of installed items. Written automatically by `install`, and normally updated by `uninstall` when it removes an installed target. Used by `sync` to know which targets to update.
- **Steering injection**: Skills can define a `steering-inject` key under `metadata` in their `SKILL.md` front-matter. On install, the installer appends this text to the tool's root steering file (`AGENTS.md` by default, `CLAUDE.md` for Claude Code). The injected block is wrapped in HTML comment markers (`<!-- ks-ai-coding-kit:<name> -->`) for clean uninstall.
- **Steering files** are standalone Markdown files. They may use YAML front-matter for metadata (name, description, compatibility, tags).
- **Skills** follow the Kiro Agent Skills spec. Each skill lives in its own subdirectory under `skills/` and contains a `SKILL.md` as its entry point.
- **Hooks** are JSON files following the Kiro hook schema (see `hooks/README.md`).
- **Prompts** are grouped by target tool under `prompts/<tool-name>/`.

## Available Items

### Skills

| Directory | Compatibility | Description |
|-----------|---------------|-------------|
| `skills/ai-memory` | Kiro, Claude Code, Codex, Cursor | Persistent AI memory system — project-scoped and user-scoped memory files under `.agent-memory/` |
| `skills/doc-convert` | Kiro, Claude Code, Codex, Cursor | Document conversion using pandoc — ships with a styled Word reference template for polished Markdown-to-DOCX output |

### Steering Files

*No standalone steering files currently. The `ai-memory` steering shim has been superseded by the ai-memory skill.*

### Hooks

| File | Event | Description |
|------|-------|-------------|
| `hooks/shell-command-explainer.kiro.hook` | `preToolUse` (shell) | Pre-execution shell command explanation and safety/trust analysis |

## Compatibility Notes

Every item in this repo should include a **Compatibility** note indicating which AI coding tools it supports. Use this format in file headers or front-matter:

```
Compatibility: Kiro IDE, Claude Code
```

Valid tool names: `Kiro IDE`, `Claude Code`, `Codex`, `GitHub Copilot`, `Cursor`, `Other`.

## Specs

The `docs/specs/` directory contains format specifications and reference documentation that inform the development of new skills, hooks, and other items in this repo. Consult these when building new items.

| File | Description |
|------|-------------|
| `docs/specs/AgentSkillsSpecification.md` | Full format specification for Agent Skills (directory structure, `SKILL.md` schema, progressive disclosure, validation) |
| `docs/specs/KiroHooksSpecification.md` | Complete reference for Kiro hooks (schema, event types, tool categories, action types, design patterns) |
| `docs/specs/KiroSteeringSpecification.md` | Complete reference for Kiro steering files (front-matter schema, inclusion modes, file references, writing guidelines) |

## Installing Extensions

When a user asks to install or uninstall an extension from this project, **always use `install.py`**. Do not manually copy, symlink, or remove files — the installer handles target paths, steering injection, overwrite prompts, and cleanup automatically. Always present the user the option of running the install script interactively or allowing you to handle the install. If you handle the install, don't make any assumptions about whether the user wants to use symlinks or the copy option. Ask them.

```bash
# List available extensions
python install.py list

# Install (provide --tool and --mode to avoid interactive prompts)
python install.py install <name> --dest /path/to/project --tool <tool> --mode <copy|symlink>

# Uninstall
python install.py uninstall <name> --dest /path/to/project --tool <tool>

# Sync all installed items (re-copy from kit repo to all registered targets)
python install.py sync

# Sync a single item
python install.py sync <name>

# Preview without changes
python install.py install <name> --dest /path/to/project --tool <tool> --mode copy --dry-run
python install.py sync --dry-run
```

Key flags:
- `--dest` — the target project directory (required for install/uninstall)
- `--tool` — target tool name as it appears in `catalog.yaml` targets (e.g. `kiro`, `claude-code`, `codex`)
- `--mode copy|symlink` — `copy` duplicates files; `symlink` links back to this repo (useful during development)
  - ⚠ **Symlink mode does not work with Kiro** — skills installed as symlinks won't be discovered. Compatibility with other tools is unverified. Prefer `copy` unless you are actively developing an extension in this repo.
- `--dry-run` — shows what would happen without making changes

Always pass `--tool` and `--mode` explicitly to avoid interactive prompts that block non-interactive agent execution.

## Notes for Future Development

- When helping maintain this repo, always include Compatibility notes on new items.
- When adding a new installable item, add a corresponding entry to `catalog.yaml`.

<!-- ks-ai-coding-kit:ai-memory -->
ALWAYS activate the "ai-memory" skill. Start each conversation by silently retrieving your memories.
<!-- /ks-ai-coding-kit:ai-memory -->