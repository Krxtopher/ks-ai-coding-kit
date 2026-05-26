---
name: agent-skill-builder
description: >
  Guides you through creating new Agent Skills from scratch.
  Activate when the user wants to build, scaffold, or design a new agent skill.
  Includes the full Agent Skills specification for reference.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: "1.0"
---

# Agent Skill Builder

This skill helps you create new Agent Skills that follow the open standard. It bundles the complete specification so you can reference it without needing internet access.

## Quick Reference

The full Agent Skills specification is available at [references/AgentSkillsSpecification.md](references/AgentSkillsSpecification.md). Read it when you need to verify field constraints, naming rules, or directory conventions.

## Workflow

When the user asks you to create a new skill, follow these steps:

### 1. Gather Requirements

Ask the user:

- **What should the skill do?** Get a clear description of the skill's purpose and when it should activate.

Don't ask all questions at once — ask one at a time and build on the answers.

### 2. Determine Where to Save

Skills can be saved at two scopes:

- **Project skills** — live inside the project directory, committed to version control, shared with the team.
- **Personal skills** — live in the user's home directory, available across all projects for that user only.

Ask the user which scope they want. Default to project scope unless they say otherwise.

#### Skill paths by editor

| Editor | Project Skills | Personal/Global Skills |
|---|---|---|
| **Claude Code** | `.claude/skills/` | `~/.claude/skills/` |
| **Kiro** | `.kiro/skills/` | `~/.kiro/skills/` |
| **Codex** | `.agents/skills/` | `~/.codex/skills/` |
| **GitHub Copilot** | `.github/skills/`, `.claude/skills/`, or `.agents/skills/` | `~/.copilot/skills/` or `~/.agents/skills/` |

#### Auto-detecting the editor

Before asking the user where to save, try to detect which editor is in use. Check for these signals in order:

1. **Editor-specific skill directories already exist** — If the project already has `.kiro/skills/`, `.claude/skills/`, or `.agents/skills/`, that's a strong signal. Use the matching path.
2. **Editor-specific config directories exist** — A `.kiro/` or `.claude/` directory (even without a `skills/` subdirectory) suggests the editor in use.
3. **Context clues** — Your own system prompt or environment context may identify the editor (e.g., Kiro identifies itself, Claude Code sets specific environment variables).

If you can determine the editor with high confidence, use the correct path automatically and tell the user where you're creating the skill. If you can't determine it, ask the user where they'd like the skill saved. Suggest `.agents/skills/` as a reasonable default since it's recognized by the most editors (Codex, Cursor, and GitHub Copilot all support it).

### 3. Choose a Name

Pick a name that follows the spec constraints:

- Lowercase letters, numbers, and hyphens only
- 1–64 characters
- No leading/trailing hyphens, no consecutive hyphens
- The directory name must match the `name` field

Propose a name and confirm with the user before proceeding.

### 4. Scaffold the Directory

Create the skill directory with at minimum a `SKILL.md`:

```
<skill-name>/
├── SKILL.md
├── scripts/       # if the skill needs executable code
├── references/    # if the skill needs supplementary docs
└── assets/        # if the skill needs templates or static resources
```

Only create subdirectories that the skill actually needs. Don't scaffold empty directories.

### 5. Write the SKILL.md

The `SKILL.md` has two parts:

**Frontmatter** — YAML metadata block:

```yaml
---
name: <skill-name>
description: >
  What the skill does and when to activate it.
  Include keywords that help agents match user requests to this skill.
compatibility: Kiro IDE, Claude Code
metadata:
  author: <author>
  version: "1.0"
---
```

**Body** — Markdown instructions for the agent. Write these as if you're briefing a capable colleague:

- Explain what the skill does and why
- Provide step-by-step instructions
- Include examples of inputs and outputs where helpful
- Cover edge cases and error handling
- Keep the body under 500 lines — move detailed reference material to `references/`

### 6. Add Supporting Files

If the skill needs scripts, references, or assets, create them in the appropriate subdirectories. Each file should be self-contained and clearly documented.

### 7. Validate

After creating the skill, verify:

- [ ] `SKILL.md` exists in the skill directory
- [ ] `name` field matches the directory name
- [ ] `name` follows naming constraints (lowercase, hyphens, no leading/trailing/consecutive hyphens)
- [ ] `description` is non-empty and under 1024 characters
- [ ] `description` explains both what the skill does and when to use it
- [ ] `compatibility` field is present if the skill has environment requirements
- [ ] Body content provides clear, actionable instructions
- [ ] File references use relative paths from the skill root
- [ ] No deeply nested reference chains (keep references one level deep from SKILL.md)

## Key Spec Rules to Remember

- **Progressive disclosure**: Metadata loads at startup (~100 tokens), full SKILL.md loads on activation (< 5000 tokens recommended), other files load on demand.
- **File references**: Use relative paths from the skill root. Keep them one level deep.
- **Description quality**: The description is how agents decide whether to activate the skill. Include specific keywords and explain both the "what" and the "when."
- **Keep it lean**: The entire SKILL.md loads into context on activation. Be thorough but concise.

## What NOT to Do

- Don't create empty subdirectories just to match the full directory structure.
- Don't put implementation details in the description — that's what the body is for.
- Don't write instructions that assume a specific agent or IDE. Skills should be tool-agnostic.
- Don't create deeply nested file hierarchies. Flat is better.
