# KS AI Coding Kit

Reusable extensions for AI coding tools — skills, hooks, and agent instructions that work across [Kiro](https://kiro.dev), [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex](https://openai.com/index/introducing-codex/), [Cursor](https://www.cursor.com/), and other AI-assisted editors.

## What's Included

### Skills

| Name | Description | Compatibility |
|------|-------------|---------------|
| [agent-memory](skills/agent-memory/SKILL.md) | Persistent memory across conversations. Supports project-scoped and user-scoped memories. | Kiro, Claude Code, Codex, Cursor |
| [bedrock-vision](skills/bedrock-vision/SKILL.md) | Analyze images using Bedrock vision models. Returns AI description plus technical metadata. | Kiro, Claude Code, Codex, Cursor |
| [current-time](skills/current-time/SKILL.md) | Looks up the current date and time in local and UTC, accurate to the second | Kiro, Claude Code, Codex, Cursor |
| [doc-convert](skills/doc-convert/SKILL.md) | Document conversion via pandoc with a styled Word template | Kiro, Claude Code, Codex, Cursor |

### Hooks

| Name | Description | Compatibility |
|------|-------------|---------------|
| [shell-command-explainer](hooks/shell-command-explainer.kiro.hook) | Explains shell commands before execution with safety analysis | Kiro |

### Agent Instructions

Reusable instruction sets — coding standards, project context, workflows — designed to be added to your project's root steering file (`AGENTS.md`, `CLAUDE.md`, etc.). No agent instructions are currently available — all capabilities have been migrated to skills.

## Quick Start

Requires Python 3.10+. No additional dependencies.

```bash
# See what's available
python install.py list

# Install a skill into your project
python install.py install agent-memory --dest ~/my-project
```

The installer prompts you to pick a target tool if the extension supports more than one. To skip the prompt (useful for scripting), pass `--tool` directly:

```bash
python install.py install agent-memory --dest ~/my-project --tool kiro
```

Uninstall works the same way:

```bash
python install.py uninstall agent-memory --dest ~/my-project
```

## Syncing Updates

Made improvements to an extension? Push them to every workspace where it's installed:

```bash
python install.py sync          # all installed items
python install.py sync agent-memory  # just one
```

The installer tracks destinations in a local `.install-manifest.json` (gitignored), so `sync` knows where to copy.

## How It Works

The installer reads `catalog.yaml` (the source of truth for all extensions) and copies files to the right location for your chosen tool. Each extension declares its own compatibility, so you only see what works with your setup.

A few things happen automatically:

- **Steering injection** — Some skills (like `agent-memory`) need a one-liner in your project's root instruction file (`AGENTS.md` or `CLAUDE.md`) to activate at conversation start. The installer appends it on install and removes it on uninstall.
- **Dry runs** — Add `--dry-run` to any command to preview changes without writing anything.
- **Manual install** — You can always copy files by hand. See the target paths in `catalog.yaml` or the tool-specific docs below.

<details>
<summary>Manual install paths by tool</summary>

| Content Type | Kiro | Claude Code | Codex / Cursor |
|-------------|------|-------------|----------------|
| Skills | `.kiro/skills/<name>` | `.claude/skills/<name>` | `.agents/skills/<name>` |
| Hooks | `.kiro/hooks/<name>` | — | — |
| Instructions | `.kiro/steering/` | `CLAUDE.md` | `AGENTS.md` |

</details>

## Concepts

New to AI coding assistants? Here's a quick glossary:

- **Agent instructions** — Markdown files that act as a persistent system prompt for your project. Different tools call them different things (steering files, rules, project instructions), but the idea is the same.
- **Skills** — Multi-file packages that teach the agent a specific capability, following the open [Agent Skills](https://agentskills.io/home) standard. Each includes a `SKILL.md` entry point with metadata and instructions, plus optional scripts and assets.
- **Hooks** — Event-driven automations (Kiro only). A hook listens for an IDE event and triggers a shell command or agent prompt in response.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Short version: add your files, create a `catalog.yaml` entry, include a Compatibility note, and open a PR.

## License

See [LICENSE](LICENSE) for details.
