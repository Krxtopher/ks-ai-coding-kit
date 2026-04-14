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
    ALWAYS activate the "ai-memory" skill. Start each conversation by silently retrieving your memories.
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

At the start of every conversation, read all files in both `.agent-memory/project/` and `.agent-memory/user/` to load prior context. Do not summarize them back to the user unless asked.

## Writing Memories

You MUST update memory files proactively. Do not wait for an ideal moment — write early and often. When in doubt, write it down.

### Proactive Memory Triggers

Use this checklist to recognize when a memory write is needed:

- **User asks you to do something** (build, fix, refactor, investigate, change) → log it as a task in `tasks.md`
- **User corrects your behavior or assumptions** → log the correction in `preferences.md`
- **You discover something surprising about the codebase** → log it in the appropriate `insights.md`
- **You make a design decision or trade-off** → log it in `project/insights.md`
- **User states a preference or habit** → log it in `preferences.md`
- **A personal technical insight comes up** → log it in `user/insights.md`
- **Conversation is ending with unfinished work** → update task status in `tasks.md`

### Task Tracking

Task tracking is a core responsibility of this memory system. Follow these rules strictly:

- **At the start of any task**, immediately create an entry in `tasks.md` with status `in-progress`. Do this before you begin the actual work. If the user asks you to build, fix, refactor, investigate, or change something — that's a task.
- **At the end of a conversation** where a task was worked on, update its status. Mark it `completed` if done, or update `Next steps` with enough context that a future session can resume without re-discovery.
- **If a task spans multiple conversations**, the entry in `tasks.md` is how you'll pick it back up. Include enough detail in `Context` and `Next steps` to make resumption seamless.
- **Before your final response in a conversation**, review whether any tasks were started or progressed, and ensure `tasks.md` is up to date. This is not optional.

### General Guidelines

- Keep entries concise — one to two lines each, except for in-flight tasks which can include more detail (status, blockers, next steps).
- Use bullet points for individual memories.
- Add a date prefix in `YYYY-MM-DD` format to each entry so stale memories can be identified.
- When a task is completed, move it from `tasks.md` or remove it. Don't let completed tasks accumulate.
- When a preference or insight is superseded, update or replace the old entry rather than adding a duplicate.
- Don't ask the user for permission to update memories. Just do it when appropriate.
- If a memory file doesn't exist yet, create it.
- Don't assume the user has visibility into how your memories are organized and stored. There's no need for the user to concern themselves with those details.

## Memory Maintenance

Memory files load into context every conversation — keep them lean.

**Limits:** Target ~100 lines per file. If a file exceeds 150 lines, prune before adding new entries.

**Pruning priority:**
1. Remove completed tasks. Distill any lasting insight into `insights.md` first.
2. Merge related entries into one.
3. Drop entries whose underlying facts have changed or no longer apply. Age alone is not a reason to remove — architectural decisions and preferences can stay indefinitely.
4. Condense verbose entries.

**When:** Prune during reading if a file is long, or during writing if near the limit. Don't announce pruning unless removing something the user might want to keep.

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
