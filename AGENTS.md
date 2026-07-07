# AGENTS.md

Agent-facing documentation for the `ks-ai-coding-kit` repository.

## Project Structure

```
ks-ai-coding-kit/
├── catalog.yaml           # Registry for non-skill items (hooks, instructions)
├── install.py             # CLI installer for hooks and agent instructions
├── agent-instructions/    # Reusable agent instruction files (single .md files)
├── skills/                # Agent Skills (each in its own subfolder with SKILL.md)
├── hooks/                 # Kiro hooks (.json files)
└── docs/                  # Project documentation
    ├── specs/             # Format specifications and reference docs for building new items
    └── IDEAS.md           # Future plans and ideas
```

## Conventions

- **Skills** follow the [Agent Skills open standard](https://agentskills.io/). Each skill lives in its own subdirectory under `skills/` and contains a `SKILL.md` as its entry point. Skills are installed into projects using `npx skills` — they are NOT in `catalog.yaml`.
- **Catalog** (`catalog.yaml`) is the registry for non-skill installable items (hooks and agent instructions). Each entry defines name, type, source path, description, compatibility, and per-tool install targets.
- **Installer** (`install.py`) reads the catalog and installs hooks/instructions to the correct location. Supports `list`, `install`, `uninstall`, `sync`, `--dry-run`, `--tool`, `--type`. No dependencies beyond Python 3.10+ (PyYAML optional).
- **Agent instructions** are standalone Markdown files under `agent-instructions/`. They may use YAML front-matter for metadata (name, description, compatibility, tags). The installer places them in the right location for each tool via append-mode targets.
- **Hooks** are JSON files following the Kiro hook schema (see `hooks/README.md`).

## Available Items

### Skills

| Directory | Compatibility | Description |
|-----------|---------------|-------------|
| `skills/agent-memory` | Kiro, Claude Code, Codex, Cursor | Persistent AI memory system — project-scoped and user-scoped memory files under `.agent-memory/` |
| `skills/agent-skill-builder` | Kiro, Claude Code, Codex, Cursor | Guides you through creating new Agent Skills from scratch, with the full specification bundled for reference |
| `skills/bedrock-vision` | Kiro, Claude Code, Codex, Cursor | Analyze images from the workspace using Bedrock vision models and extract technical metadata (dimensions, file size, MIME type, bit depth, channels) |
| `skills/current-time` | Kiro, Claude Code, Codex, Cursor | Looks up the current date and time in both local time and UTC, accurate to the second |
| `skills/doc-convert` | Kiro, Claude Code, Codex, Cursor | Document conversion using pandoc — ships with a styled Word reference template for polished Markdown-to-DOCX output |
| `skills/git-guardian` | Kiro, Claude Code, Codex, Cursor | Git commit and branching guardian — scans for secrets, large files, archives, and notebook output before committing |
| `skills/mermaid-diagram` | Kiro, Claude Code, Codex, Cursor | Generates static PNG images from Mermaid diagram definitions using the local Mermaid CLI |
| `skills/narrator-kokoro` | Kiro, Claude Code, Codex, Cursor | Text-to-speech narrator using Kokoro (local ONNX model) — fast, fully offline speech synthesis with zero API keys or cloud dependencies |
| `skills/narrator-elevenlabs` | Kiro, Claude Code, Codex, Cursor | Text-to-speech narrator using ElevenLabs streaming API — high-quality cloud voices with low-latency playback |
| `skills/narrator-polly` | Kiro, Claude Code, Codex, Cursor | Text-to-speech narrator using Amazon Polly generative engine — zero API key setup, uses AWS credentials, low-latency streaming playback |
| `skills/tutorial-jupyter-notebook` | Kiro, Claude Code, Codex, Cursor | Guide for creating high-quality educational Jupyter Notebooks that teach workflows, patterns, and technical concepts |

### Agent Instructions

| File | Compatibility | Description |
|------|---------------|-------------|
| `agent-instructions/documentation-standards.md` | Kiro, Claude Code, Codex, Cursor | Guidelines for when and how to update README.md and agent-facing docs |

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

### Skills

Use `npx skills` to install skills from this project into a target project:

```bash
# Install a specific skill
npx skills add <path-to-this-repo>/skills --skill <name> --agent <agent> -y

# Install from GitHub
npx skills add Krxtopher/ks-ai-coding-kit --skill <name> --agent <agent> -y

# Install all skills for all agents
npx skills add Krxtopher/ks-ai-coding-kit --all

# List installed skills
npx skills list

# Update all installed skills
npx skills update -y

# Remove a skill
npx skills remove <name> --agent <agent> -y
```

Agent names: `kiro-cli`, `claude-code`, `codex`, `cursor`. Use `*` for all agents.

Always pass `-y` to skip confirmation prompts in non-interactive agent execution.

### Hooks & Agent Instructions

Non-skill extensions use `install.py`:

```bash
python install.py list
python install.py install <name> --dest /path/to/project --tool <tool>
python install.py uninstall <name> --dest /path/to/project --tool <tool>
```

Always pass `--tool` explicitly to avoid interactive prompts that block non-interactive agent execution.

## Notes for Future Development

- When helping maintain this repo, always include Compatibility notes on new items.
- When adding a new skill, create its directory under `skills/` with a `SKILL.md` entry point.
- When adding a new non-skill item (hook or instruction), add a corresponding entry to `catalog.yaml`.


<!-- ks-ai-coding-kit:agent-memory -->
ALWAYS activate the "agent-memory" skill. Start each conversation by silently retrieving your memories.
<!-- /ks-ai-coding-kit:agent-memory -->