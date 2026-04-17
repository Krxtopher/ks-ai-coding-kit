# Agent Skills

Reusable agent skills — packaged capabilities that extend what your AI coding assistant can do.

## What Are Skills?

Skills are multi-file packages that define a specific capability for an AI coding agent. Each skill lives in its own directory and includes a `SKILL.md` entry point that describes the skill's purpose, inputs, and behavior. Skills follow the [Agent Skills open standard](https://agents.md) and work across compatible tools.

## Compatibility

Skills in this collection are designed to work with any AI coding tool that supports the Agent Skills standard. Each skill's `SKILL.md` front-matter lists its specific tool compatibility.

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
| `doc-convert/` | Convert documents between formats using pandoc — ships with a styled Word reference template for polished Markdown-to-DOCX output |
