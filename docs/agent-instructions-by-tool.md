# Agent Instructions File Locations by AI Coding Tool

> Reference guide for where each AI coding tool expects its primary agent instructions to be saved.
> Last updated: April 2026.

## Quick Reference

| Tool | Primary File(s) | Location | Also Reads |
|------|-----------------|----------|------------|
| **Kiro** | `*.md` steering files | `.kiro/steering/` | `AGENTS.md` at repo root or `~/.kiro/steering/` |
| **Claude Code** | `CLAUDE.md` | Repo root | `AGENTS.md` (fallback), `~/.claude/CLAUDE.md` (global), subdirectory `CLAUDE.md` files |
| **OpenAI Codex CLI** | `AGENTS.md` | Repo root | Subdirectory `AGENTS.md` files, `~/.codex/instructions.md` (global) |
| **GitHub Copilot** | `.github/copilot-instructions.md` | `.github/` directory | `AGENTS.md` anywhere in repo, `.github/instructions/*.instructions.md` (scoped) |
| **Cursor** | `.cursor/rules/*.mdc` | `.cursor/rules/` directory | `AGENTS.md` at repo root, `.cursorrules` (legacy) |
| **Windsurf** | `.windsurf/rules/*.md` | `.windsurf/rules/` directory | `.windsurfrules` (legacy) |
| **Gemini CLI** | `GEMINI.md` | Repo root | `~/.gemini/GEMINI.md` (global), subdirectory `GEMINI.md` files |
| **Amazon Q Developer** | `.amazonq/rules/**/*.md` | `.amazonq/rules/` directory | `AmazonQ.md` at repo root, `README.md` |

## AGENTS.md — The Cross-Tool Standard

`AGENTS.md` is an open standard governed by the [Agentic AI Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) under the Linux Foundation. It is a plain Markdown file placed at the repository root (and optionally in subdirectories) that provides AI coding agents with project-specific context. As of early 2026, it has been adopted by 60,000+ open-source repositories.

Tools with confirmed `AGENTS.md` support: **Codex CLI** (primary), **GitHub Copilot**, **Cursor**, **Claude Code** (fallback), **Amp**, **Devin**, **Continue.dev**, **Aider**, **OpenHands**, and **Android Studio (Gemini)**.

Sources: [Linux Foundation announcement](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation), [vibecoding.app guide](https://vibecoding.app/blog/agents-md-guide), [deployhq.com comparison](https://deployhq.com/blog/ai-coding-config-files-guide)

---

## Tool Details

### Kiro

Kiro uses **steering files** — Markdown documents in `.kiro/steering/` — as its primary agent instructions mechanism.

- **Workspace steering**: `.kiro/steering/*.md` — applies to the current workspace only.
- **Global steering**: `~/.kiro/steering/*.md` — applies to all workspaces. Workspace steering takes precedence over global on conflicts.
- **AGENTS.md support**: Kiro reads `AGENTS.md` files placed at the repo root or in `~/.kiro/steering/`. These are always included (no conditional activation).
- **Inclusion modes**: Steering files support three modes via front-matter — `always` (default), `fileMatch` (conditional on file patterns), and `manual` (user-invoked via `#` in chat).

Steering files are plain Markdown. There is no required front-matter for basic use.

Source: [Kiro steering docs](https://kiro.dev/docs/cli/steering/)

### Claude Code

Claude Code reads `CLAUDE.md` files from multiple locations, merged in order of specificity:

1. `~/.claude/CLAUDE.md` — Global personal instructions (all projects).
2. `./CLAUDE.md` — Project root instructions (shared via git).
3. Subdirectory `CLAUDE.md` files — Scoped to specific parts of the codebase.

**AGENTS.md fallback**: If no `CLAUDE.md` is found in a directory, Claude Code reads `AGENTS.md` from that location instead. This makes `AGENTS.md` a viable single-file strategy for multi-tool teams.

> [!TIP]
> Keep `CLAUDE.md` under ~300 lines. Claude Code's system prompt uses ~50 of the ~150–200 instructions an LLM can reliably follow.

Sources: [Claude Code context guide](https://blog.datalakehouse.help/posts/2026-03-context-claude-code/), [deployhq.com comparison](https://deployhq.com/blog/ai-coding-config-files-guide)

### OpenAI Codex CLI

Codex CLI uses `AGENTS.md` as its primary configuration file. It has the most sophisticated discovery process among the tools:

- Walks from the project root down to the current working directory, loading `AGENTS.md` at each level.
- Supports `AGENTS.override.md` for local overrides (not committed to git).
- Global instructions: `~/.codex/instructions.md`.
- Fallback filenames and size limits are configurable in `~/.codex/config.toml`:
  ```toml
  project_doc_fallback_filenames = ["TEAM_GUIDE.md", ".agents.md"]
  project_doc_max_bytes = 65536
  ```

Source: [deployhq.com comparison](https://deployhq.com/blog/ai-coding-config-files-guide), [Codex CLI cheatsheet](https://shipyard.build/blog/codex-cli-cheat-sheet/)

### GitHub Copilot

GitHub Copilot supports three layers of custom instructions:

1. **Repository-wide**: `.github/copilot-instructions.md` — applied to all requests in the repo.
2. **Path-specific**: `.github/instructions/*.instructions.md` — scoped via glob patterns in YAML front-matter:
   ```yaml
   ---
   applyTo: "**/*.tsx"
   ---
   ```
3. **Agent instructions**: `AGENTS.md` files stored anywhere in the repo. The nearest `AGENTS.md` in the directory tree takes precedence. Copilot also reads `CLAUDE.md` and `GEMINI.md` at the repo root as alternatives.

Source: [GitHub Copilot docs](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)

### Cursor

Cursor has evolved through two formats:

- **Legacy**: `.cursorrules` file at the project root. Still supported but deprecated.
- **Current** (recommended): `.cursor/rules/` directory containing `.mdc` files (Markdown Configuration) with YAML front-matter. Each file has an activation mode:
  - `alwaysApply: true` — included in every interaction.
  - `globs: ["**/*.tsx"]` — auto-attached when matching files are open.
  - `description: "..."` (no globs, no alwaysApply) — model decides whether to apply based on the description.
  - Manual — only when explicitly mentioned via `@`.

Cursor also reads `AGENTS.md` at the repo root alongside its native rules.

Source: [Cursor rules docs](https://docs.cursor.com/context/rules), [deployhq.com comparison](https://deployhq.com/blog/ai-coding-config-files-guide)

### Windsurf

Windsurf follows a similar evolution to Cursor:

- **Legacy**: `.windsurfrules` file at the project root.
- **Current**: `.windsurf/rules/` directory with individual Markdown rule files. Rules can be Always On, Manual (via `@` mention), or Model Decision.
- **Global rules**: Configured in Windsurf Settings under AI > Rules, or `~/.codeium/windsurf/global_rules.md`.

> [!NOTE]
> Individual rule files are capped at 6,000 characters, and total combined rules must not exceed 12,000 characters.

Source: [Windsurf context guide](https://blog.datalakehouse.help/posts/2026-03-context-windsurf/), [deployhq.com comparison](https://deployhq.com/blog/ai-coding-config-files-guide)

### Gemini CLI

Gemini CLI uses `GEMINI.md` with a hierarchical discovery system:

1. `~/.gemini/GEMINI.md` — Global defaults for all projects.
2. Project root `GEMINI.md` — Project-level instructions.
3. Subdirectory `GEMINI.md` files — Discovered dynamically when tools access files in those directories.

More specific sources take precedence over general ones. The filename is configurable via `settings.json`. Use `/memory show` to inspect loaded context and `/memory refresh` to force a reload.

**Android Studio (Gemini)** reads `AGENTS.md` files placed anywhere in the project.

Source: [Gemini CLI docs](https://gemini-cli.xyz/docs/en/cli/gemini-md), [Android Studio docs](https://developer.android.com/studio/gemini/agent-files)

### Amazon Q Developer

Amazon Q Developer (IDE and CLI) uses project rules stored as Markdown files:

- **Project rules**: `.amazonq/rules/**/*.md` — automatically loaded into agent context.
- **Default resources** (CLI): The built-in default agent also reads `AmazonQ.md` and `README.md` from the repo root.
- **Custom agents**: Defined as JSON files in `.amazonq/cli-agents/` (workspace) or `~/.aws/amazonq/cli-agents/` (global).

Amazon Q Developer does **not** natively read `AGENTS.md` in its default configuration. To provide cross-tool instructions, either duplicate content into `.amazonq/rules/` or create a custom agent that includes `AGENTS.md` as a resource.

Source: [Amazon Q Developer rules blog](https://aws.amazon.com/blogs/devops/mastering-amazon-q-developer-with-rules/), [Q CLI default agent behavior](https://github.com/aws/amazon-q-developer-cli/blob/main/docs/default-agent-behavior.md)

---

## Multi-Tool Strategy

For teams using multiple AI coding tools, a practical approach is:

1. **Start with `AGENTS.md`** at the repo root as the single source of truth. It has the widest cross-tool support.
2. **Add tool-specific files only when needed** — for features like Cursor's scoped activation, Copilot's glob patterns, or Kiro's conditional steering.
3. **For Claude Code**, a minimal `CLAUDE.md` can simply reference the shared instructions:
   ```markdown
   Strictly follow the rules in ./AGENTS.md
   ```
4. **For Amazon Q Developer**, create a rule file at `.amazonq/rules/agents.md` that mirrors or references `AGENTS.md` content.

Content was rephrased for compliance with licensing restrictions. See inline source links for original documentation.
