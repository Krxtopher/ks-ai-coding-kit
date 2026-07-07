---
name: skill-installer
description: >-
  Teaches the agent how to install, update, remove, and list Agent Skills
  using the npx skills CLI.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: 1.0
---

# Skill Installer

Use `npx skills` to manage Agent Skills in a project. This is the preferred way to install, update, and remove skills.

## Agent Names

When specifying `--agent`, use one of: `kiro-cli`, `claude-code`, `codex`, `cursor`. Use `*` for all agents.

## Commands

### Install a skill from a local path

```bash
npx skills add <path> --skill <name> --agent <agent> -y
```

Example — install from a local skills directory:
```bash
npx skills add ./skills --skill agent-memory --agent kiro-cli -y
```

### Install a skill from GitHub

```bash
npx skills add <owner/repo> --skill <name> --agent <agent> -y
```

### Install all skills from a source

```bash
npx skills add <source> --all
```

### List installed skills

```bash
npx skills list
npx skills list --json
```

### Update skills

```bash
npx skills update -y          # update all
npx skills update <name> -y   # update one
```

### Remove a skill

```bash
npx skills remove <name> --agent <agent> -y
```

### Restore from lock file

```bash
npx skills experimental_install
```

## Key Flags

| Flag | Purpose |
|------|---------|
| `-y, --yes` | Skip confirmation prompts (required for non-interactive use) |
| `--skill <name>` | Select specific skill(s) from a multi-skill source |
| `--agent <agent>` | Target specific agent(s) |
| `--all` | Shorthand for `--skill '*' --agent '*' -y` |
| `--copy` | Copy files instead of symlinking |
| `-g, --global` | Operate on global (user-level) skills |
