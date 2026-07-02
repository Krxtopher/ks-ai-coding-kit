# Agent Hooks

Reusable Kiro hooks that automate agent actions based on IDE events.

## What Are Hooks?

Hooks are JSON configuration files that map IDE events (file changes, prompt submissions, tool usage, etc.) to automated actions. When the event fires, the agent either runs a shell command or receives a follow-up prompt.

## Compatibility

Hooks in this collection target **Kiro IDE**, which loads them from `.kiro/hooks/` in your workspace.

## Installation

Copy any hook file into your workspace:

```bash
cp hooks/<hook>.json /path/to/your/project/.kiro/hooks/
```

## Schema

```json
{
  "name": "string (required)",
  "version": "string (required)",
  "description": "string (optional)",
  "when": {
    "type": "fileEdited | fileCreated | fileDeleted | userTriggered | promptSubmit | agentStop | preToolUse | postToolUse | preTaskExecution | postTaskExecution",
    "patterns": ["array of file glob patterns (file events only)"],
    "toolTypes": ["array of tool categories or regex (preToolUse/postToolUse only)"]
  },
  "then": {
    "type": "askAgent | runCommand",
    "prompt": "string (askAgent only)",
    "command": "string (runCommand only)"
  }
}
```

## Event Types

| Event | Trigger |
|-------|---------|
| `fileEdited` | User saves a file |
| `fileCreated` | User creates a new file |
| `fileDeleted` | User deletes a file |
| `userTriggered` | User manually triggers the hook |
| `promptSubmit` | User sends a message to the agent |
| `agentStop` | Agent execution completes |
| `preToolUse` | Before a tool is executed |
| `postToolUse` | After a tool is executed |
| `preTaskExecution` | Before a spec task starts |
| `postTaskExecution` | After a spec task completes |

## Contents

| File | Description | Event |
|------|-------------|-------|
| `shell-command-explainer.kiro.hook` | Explains what a shell command will do before execution and provides a safety/trust analysis for auto-approval decisions | `preToolUse` (shell) |
