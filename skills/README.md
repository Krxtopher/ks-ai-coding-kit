# Agent Skills

Reusable Kiro Agent Skills — packaged capabilities that extend what the AI agent can do.

## What Are Skills?

Skills are multi-file packages that define a specific capability for the Kiro IDE agent. Each skill lives in its own directory and includes a `SKILL.md` entry point that describes the skill's purpose, inputs, and behavior.

## Compatibility

Skills in this collection target **Kiro IDE**, which loads them from `.kiro/skills/` in your workspace.

## Installation

Copy a skill's entire directory into your workspace:

```bash
cp -r skills/<skill-name> /path/to/your/project/.kiro/skills/
```

## Format

Each skill directory must contain a `SKILL.md` with front-matter:

```yaml
---
name: My Skill
description: What this skill does
---
```

The rest of `SKILL.md` contains the detailed instructions the agent follows when the skill is activated.

## Contents

| Directory | Description |
|-----------|-------------|
| `ai-memory/` | Persistent AI memory system with project-scoped and user-scoped memory files for retaining context across conversations |
