---
name: ai-memory
description: >
  Persistent AI memory system with project-scoped and user-scoped memory files.
  Activate at the start of every conversation to load prior context.
  Use when you need to remember preferences, insights, tasks, or project knowledge across sessions.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: "1.0"
  steering-inject: >
    ALWAYS activate the "ai-memory" skill. Start each conversation briefly mentioning that you are retrieving your memories.
---

# AI Memory System

You have a persistent memory system under `.agent-memory/`, split into two scopes:

- **`.agent-memory/project/`** — Project-scoped memories, committed to Git. Contains knowledge that benefits the whole team: architectural decisions, project-specific gotchas, task history, and technical insights about this codebase.
- **`.agent-memory/user/`** — User-scoped memories, gitignored. Contains personal preferences, workflow habits, tool choices, and anything specific to an individual developer.

## Deciding Which Scope

Use a simple heuristic: **if the memory would be useful to another developer on this project, it's project-scoped. Otherwise, it's user-scoped.**

## Memory Files

| File | Scope | Purpose |
|---|---|---|
| `.agent-memory/project/insights.md` | Project | Technical insights, lessons learned, gotchas about this codebase |
| `.agent-memory/project/tasks.md` | Project | In-flight tasks, ongoing projects, and their current status |
| `.agent-memory/user/preferences.md` | User | Personal preferences, workflow habits, tool choices, style preferences |
| `.agent-memory/user/insights.md` | User | Personal technical insights not relevant to the team |

## Reading Memories

At the start of every conversation, read all files in both `.agent-memory/project/` and `.agent-memory/user/` to load prior context. Do this silently — don't announce that you're reading memories or summarize them back to the user unless asked.

## Writing Memories

Update memory files whenever you discover something worth remembering. This includes:

- A user preference or habit → `.agent-memory/user/preferences.md`
- A technical insight or gotcha about this project → `.agent-memory/project/insights.md`
- A personal technical insight → `.agent-memory/user/insights.md`
- A new task being started, or progress/completion of an existing task → `.agent-memory/project/tasks.md`
- A correction the user makes to your behavior or assumptions → `.agent-memory/user/preferences.md`

### Guidelines

- Keep entries concise — one to two lines each, except for in-flight tasks which can include more detail (status, blockers, next steps).
- Use bullet points for individual memories.
- Add a date prefix in `YYYY-MM-DD` format to each entry so stale memories can be identified.
- When a task is completed, move it from `tasks.md` or remove it. Don't let completed tasks accumulate.
- When a preference or insight is superseded, update or replace the old entry rather than adding a duplicate.
- Don't ask the user for permission to update memories. Just do it when appropriate.
- If a memory file doesn't exist yet, create it.
- Don't assume the user has visibility into how your memories are organized and stored. There's no need for the user to concern themselves with those details.

## File Format

Each memory file should use this structure:

```markdown
# [Category Name]

- `YYYY-MM-DD` — Memory content here
- `YYYY-MM-DD` — Another memory
```

For tasks, use a richer format:

```markdown
# Tasks

## Task Title
- **Status:** in-progress | blocked | completed
- **Started:** YYYY-MM-DD HH:MM
- **Updated:** YYYY-MM-DD HH:MM
- **Context:** Brief description of what we're doing and why
- **Next steps:** What remains to be done
```
