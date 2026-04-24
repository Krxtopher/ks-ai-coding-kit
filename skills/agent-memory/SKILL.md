---
name: agent-memory
description: >
  Persistent AI memory system with project-scoped and user-scoped memory files.
  Activate at the start of every conversation to load prior context.
  Use when you need to remember preferences, insights, tasks, or project knowledge across sessions.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: "2.0"
  steering-inject: >
    ALWAYS activate the "agent-memory" skill. Start each conversation by silently retrieving your memories.
---

# AI Memory System

You have a persistent memory system with two files under `.agent-memory/`:

| File | Scope | Purpose |
|---|---|---|
| `.agent-memory/project.md` | Project | Committed to Git. Knowledge that benefits the whole team: architectural decisions, project-specific gotchas, task history, lessons learned, and technical insights about this codebase. |
| `.agent-memory/user.md` | User | Gitignored. Personal preferences, conversation topics, and anything specific to an individual developer. |

## Deciding Which Scope

Ask: **would a different developer on this same project benefit from this information?** If yes, it's project-scoped. If it only matters to the individual you're talking to, it's user-scoped.

**When in doubt, prefer `project.md`.** Project-scoped content that happens to be personal is less harmful than project knowledge that gets gitignored and lost.

> [!IMPORTANT]
> The source of the information doesn't determine the scope. Instructions that come from a single user are often project standards — file organization conventions, naming rules, directory structure, coding patterns, and workflow requirements all belong in `project.md` even if only one person stated them.

## File Structure

Each file uses top-level headings to separate concerns. Write entries under the appropriate heading.

**`.agent-memory/project.md`** contains:

```markdown
# Insights
- `YYYY-MM-DD` — Technical insights, lessons learned, gotchas about this codebase

# Tasks
## Task Title
- **Status:** in-progress | blocked | completed
- **Started:** YYYY-MM-DD
- **Updated:** YYYY-MM-DD
- **Context:** Brief description of what we're doing and why
- **Next steps:** What remains to be done
```

**`.agent-memory/user.md`** contains:

```markdown
# Preferences
- `YYYY-MM-DD` — Personal preferences, workflow habits, tool choices, style preferences

# Topics
- `YYYY-MM-DD` — Rolling log of recent conversation topics for continuity across sessions
```

## Reading Memories

At the start of every conversation, read both `.agent-memory/project.md` and `.agent-memory/user.md` to load prior context. Do not summarize them back to the user unless asked.

## Writing Memories

You MUST update memory files proactively. Do not wait for an ideal moment — write early and often. When in doubt, write it down. Write entries under the correct heading within the appropriate file.

### Proactive Memory Triggers

Use this checklist to recognize when a memory write is needed:

- **User asks you to do something** (build, fix, refactor, investigate, change) → log it under `# Tasks` in `project.md`
- **User corrects your behavior or assumptions about the project** (e.g., "we use PostgreSQL not MySQL", "data files go in `data/`") → log it under `# Insights` in `project.md`
- **User corrects your personal interaction style** (e.g., "be more concise", "don't use emojis") → log it under `# Preferences` in `user.md`
- **You discover something surprising about the codebase** → log it under `# Insights` in `project.md`
- **You make a design decision or trade-off** → log it under `# Insights` in `project.md`
- **User states a project convention or standard** (file organization, naming, directory structure, required patterns) → log it under `# Insights` in `project.md`
- **User states a personal preference or habit** (communication style, editor settings, workflow quirks) → log it under `# Preferences` in `user.md`
- **Conversation is ending with unfinished work** → update task status under `# Tasks` in `project.md`
- **A new conversation topic comes up** → log it under `# Topics` in `user.md` (see Conversation Topic Tracking below)

### Task Tracking

Task tracking is a core responsibility of this memory system. Follow these rules strictly:

- **At the start of any task**, immediately create an entry under `# Tasks` in `project.md` with status `in-progress`. Do this before you begin the actual work. If the user asks you to build, fix, refactor, investigate, or change something — that's a task.
- **At the end of a conversation** where a task was worked on, update its status. Mark it `completed` if done, or update `Next steps` with enough context that a future session can resume without re-discovery.
- **If a task spans multiple conversations**, the entry in `project.md` is how you'll pick it back up. Include enough detail in `Context` and `Next steps` to make resumption seamless.
- **Before your final response in a conversation**, review whether any tasks were started or progressed, and ensure `# Tasks` in `project.md` is up to date. This is not optional.

### Conversation Topic Tracking

Not every conversation involves a task. The user might ask a question, discuss an idea, or explore a topic without any actionable outcome. These conversations still matter for continuity — the user may return later and expect you to remember what you were discussing.

Track conversation topics under `# Topics` in `user.md`. This section holds a short rolling log of recent topics, so you always know what was last discussed even if it wasn't task-related.

**When to write:**
- At the start of a conversation, once the topic is clear, log a one-line summary.
- If the conversation shifts to a substantially different topic mid-session, log the new topic.
- You don't need to log every minor tangent — just meaningful topic changes.

**What to write:** A brief, natural description of the topic. Examples:
- `2025-07-10` — Discussed pros and cons of DynamoDB single-table design
- `2025-07-10` — Helped debug a CloudFormation stack rollback issue
- `2025-07-11` — Chatted about whether to migrate from Jest to Vitest

**Maintenance:** Keep only the 10 most recent entries. When adding a new one, drop the oldest if at the limit. This section should stay very short.

### General Guidelines

- Keep entries concise — one to two lines each, except for in-flight tasks which can include more detail (status, blockers, next steps).
- Use bullet points for individual memories.
- Add a date prefix in `YYYY-MM-DD` format to each entry so stale memories can be identified.
- **Order entries newest-first** within each section. New entries go at the top of their section, just below the heading. This puts the most recent and relevant context at the top where it's seen first.
- When a task is completed, remove it from `# Tasks`. Don't let completed tasks accumulate. Distill any lasting insight into `# Insights` first.
- When a preference or insight is superseded, update or replace the old entry rather than adding a duplicate.
- Don't ask the user for permission to update memories. Just do it when appropriate.
- If a memory file doesn't exist yet, create it with the appropriate section headings.
- Do not add headings beyond `# Preferences` and `# Topics` in `user.md`. If content doesn't fit those two categories, it likely belongs in `project.md`.
- Don't assume the user has visibility into how your memories are organized and stored. There's no need for the user to concern themselves with those details.

### What Does NOT Belong in `user.md`

These are project-scoped even when stated by a single user:
- Architectural or design decisions
- File organization conventions and directory structure rules
- Codebase discoveries, gotchas, or technical insights
- Task context or status
- Naming conventions, coding patterns, or workflow requirements
- Anything another developer on the team would benefit from knowing

## Memory Maintenance

Memory files load into context every conversation — keep them lean.

**Limits:** Target ~150 lines per file. If a file exceeds 200 lines, prune before adding new entries.

**Pruning priority:**
1. Remove completed tasks. Distill any lasting insight into `# Insights` first.
2. Merge related entries into one.
3. Drop entries whose underlying facts have changed or no longer apply. Age alone is not a reason to remove — architectural decisions and preferences can stay indefinitely.
4. Condense verbose entries.

**When:** Prune during reading if a file is long, or during writing if near the limit. Don't announce pruning unless removing something the user might want to keep.
