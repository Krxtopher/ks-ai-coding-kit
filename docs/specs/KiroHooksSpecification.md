# Kiro Hooks Specification

> Complete reference for building event-driven agent hooks in Kiro IDE.

## Overview

A hook is a JSON configuration file that maps an IDE event to an automated action. When the event fires, Kiro either sends a follow-up prompt to the agent (`askAgent`) or executes a shell command (`runCommand`). Hooks live in `.kiro/hooks/` inside your workspace and are loaded automatically.

Hooks are useful for enforcing standards, running linters on save, explaining commands before execution, gating destructive operations, kicking off builds after task completion, and any other workflow you want to automate around agent activity.

## File Location and Naming

```
<workspace>/
└── .kiro/
    └── hooks/
        ├── lint-on-save.kiro.hook
        ├── review-writes.kiro.hook
        └── ...
```

- Hook files use the `.kiro.hook` extension by convention.
- The file itself is JSON (not JSONC — no comments allowed).
- Kiro watches the `.kiro/hooks/` directory and picks up changes automatically.

## Schema

Every hook file must conform to this structure:

```json
{
  "name": "string (required)",
  "version": "string (required)",
  "description": "string (optional)",
  "enabled": true,
  "when": {
    "type": "string (required — one of the event types below)",
    "patterns": ["array of glob strings (required for file events only)"],
    "toolTypes": ["array of tool categories or regex patterns (required for preToolUse / postToolUse only)"]
  },
  "then": {
    "type": "string (required — askAgent or runCommand)",
    "prompt": "string (required when then.type is askAgent)",
    "command": "string (required when then.type is runCommand)"
  }
}
```

### Top-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Human-readable name for the hook. Shown in the Kiro UI. |
| `version` | Yes | string | Version string (e.g. `"1.0.0"` or `"1"`). Informational only. |
| `description` | No | string | Longer explanation of what the hook does and why. |
| `enabled` | No | boolean | Set to `false` to disable the hook without deleting it. Defaults to `true`. |

### `when` Block

The `when` block defines the trigger.

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `type` | Yes | string | The event type (see Event Types below). |
| `patterns` | Conditional | string[] | Glob patterns for file-based events (`fileEdited`, `fileCreated`, `fileDeleted`). Required when `type` is a file event. |
| `toolTypes` | Conditional | string[] | Tool categories or regex patterns. Required when `type` is `preToolUse` or `postToolUse`. |

### `then` Block

The `then` block defines the action to take when the event fires.

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `type` | Yes | string | Either `askAgent` or `runCommand`. |
| `prompt` | Conditional | string | The prompt sent to the agent. Required when `type` is `askAgent`. |
| `command` | Conditional | string | The shell command to execute. Required when `type` is `runCommand`. |

## Event Types

### File Events

These fire when the user interacts with files in the workspace. They require the `patterns` array in the `when` block.

| Event | Fires When |
|-------|-----------|
| `fileEdited` | A file is saved by the user. |
| `fileCreated` | A new file is created. |
| `fileDeleted` | A file is deleted. |

`patterns` uses standard glob syntax:

- `*.ts` — all TypeScript files in the workspace root
- `**/*.py` — all Python files recursively
- `src/**/*.tsx` — TSX files under `src/`
- `*.{js,ts}` — JS and TS files

**Example — lint TypeScript on save:**

```json
{
  "name": "Lint on Save",
  "version": "1.0.0",
  "when": {
    "type": "fileEdited",
    "patterns": ["**/*.ts", "**/*.tsx"]
  },
  "then": {
    "type": "runCommand",
    "command": "npm run lint"
  }
}
```

### Tool Events

These fire before or after the agent uses a tool. They require the `toolTypes` array in the `when` block.

| Event | Fires When |
|-------|-----------|
| `preToolUse` | Immediately before a tool is about to be executed. |
| `postToolUse` | Immediately after a tool has finished executing. |


#### Tool Categories

`toolTypes` accepts built-in category names and/or regex patterns:

| Category | Matches |
|----------|---------|
| `read` | File reading tools (readFile, readCode, readMultipleFiles, etc.) |
| `write` | File writing tools (fsWrite, fsAppend, strReplace, deleteFile, etc.) |
| `shell` | Shell/terminal execution tools (executeBash, controlBashProcess, etc.) |
| `web` | Web access tools (web search, web fetch) |
| `spec` | Spec-related tools |
| `*` | All tools (wildcard) |

For MCP (Model Context Protocol) tools or other custom tools, use a regex pattern to match tool names:

- `".*sql.*"` — matches any tool with "sql" in the name
- `".*database.*"` — matches database-related tools
- `"my-server_.*"` — matches all tools from a specific MCP server

You can mix categories and regex patterns in the same array:

```json
"toolTypes": ["write", ".*sql.*"]
```

**Example — review all write operations:**

```json
{
  "name": "Review Write Operations",
  "version": "1.0.0",
  "when": {
    "type": "preToolUse",
    "toolTypes": ["write"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Verify this write operation follows our coding standards before proceeding."
  }
}
```

**Example — log tool results:**

```json
{
  "name": "Log Tool Results",
  "version": "1.0.0",
  "when": {
    "type": "postToolUse",
    "toolTypes": ["shell"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Review the shell command output for errors or warnings and summarize any issues."
  }
}
```

#### preToolUse Behavior

`preToolUse` hooks are special because they run *before* the tool executes, giving the agent (or a command) a chance to inspect, gate, or modify the operation.

Key behaviors:

1. **Access control**: If the hook's output indicates that access is denied or permission is refused, the agent **must not** retry the tool call. The operation is blocked.
2. **Proceed on no denial**: If the hook output shows no indication of access denial, the agent re-invokes the tool to complete the operation.
3. **Parameter preservation**: Unless the hook output explicitly says parameters need to change, the agent must re-invoke the tool with exactly the same parameters.
4. **Circular dependency detection**: A `preToolUse` hook can accidentally create an infinite loop if its action triggers the same tool category it's watching. For example, a hook on `write` tools that asks the agent to write a log file would trigger itself. When the agent detects this circular pattern, it honors the top-level hook but skips nested re-triggers. However, if a nested hook explicitly denies access, the denial is always respected.

### Prompt and Agent Lifecycle Events

These fire at specific points in the agent conversation lifecycle. They do not require `patterns` or `toolTypes`.

| Event | Fires When |
|-------|-----------|
| `promptSubmit` | The user sends a message to the agent. |
| `agentStop` | The agent finishes its current execution. |

**Example — remind the agent of project conventions on every prompt:**

```json
{
  "name": "Convention Reminder",
  "version": "1.0.0",
  "when": {
    "type": "promptSubmit"
  },
  "then": {
    "type": "askAgent",
    "prompt": "Remember: use PEP 8 style, type hints on all functions, and logging instead of print."
  }
}
```

### Task Events

These fire around spec task execution. They do not require `patterns` or `toolTypes`.

| Event | Fires When |
|-------|-----------|
| `preTaskExecution` | Before a spec task's status is set to `in_progress`. |
| `postTaskExecution` | After a spec task's status is set to `completed`. |

**Example — run tests after each spec task completes:**

```json
{
  "name": "Run Tests After Task",
  "version": "1.0.0",
  "when": {
    "type": "postTaskExecution"
  },
  "then": {
    "type": "runCommand",
    "command": "npm run test"
  }
}
```

### Manual Trigger

| Event | Fires When |
|-------|-----------|
| `userTriggered` | The user manually clicks the hook's run button in the Kiro UI. |

This is useful for on-demand actions that don't map to a specific IDE event — one-off builds, deployments, report generation, etc.

**Example — manual deployment:**

```json
{
  "name": "Deploy to Staging",
  "version": "1.0.0",
  "description": "Manually trigger a deployment to the staging environment.",
  "when": {
    "type": "userTriggered"
  },
  "then": {
    "type": "runCommand",
    "command": "bash deploy.sh staging"
  }
}
```

## Action Types

### `askAgent`

Sends a prompt to the agent as a follow-up message. The agent processes the prompt in the context of the current conversation, including any information about the triggering event (the file that changed, the tool that's about to run, etc.).

Use `askAgent` when you want the agent to:
- Review or analyze something before or after an operation
- Enforce conventions or standards
- Provide explanations or summaries
- Make decisions based on context

The `prompt` field supports multi-line strings (use `\n` for line breaks in JSON).

### `runCommand`

Executes a shell command in the workspace root. The command runs in the same environment as the user's terminal.

Use `runCommand` when you want to:
- Run linters, formatters, or test suites
- Execute build scripts
- Run any deterministic CLI operation

The command's stdout/stderr is captured and made available to the agent. If the command fails (non-zero exit code), the agent sees the error output.

**Timeout**: `runCommand` actions have a default timeout of 60 seconds. This can be configured when creating hooks programmatically. Set to 0 to disable the timeout.

## Design Patterns

### Gate Pattern (preToolUse + askAgent)

Use a `preToolUse` hook with `askAgent` to review operations before they happen. The agent inspects the pending operation and either allows it to proceed or flags concerns.

```json
{
  "name": "SQL Query Review",
  "version": "1.0.0",
  "when": {
    "type": "preToolUse",
    "toolTypes": [".*sql.*"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Review this database operation. If it modifies or deletes data, warn the user and ask for confirmation before proceeding."
  }
}
```

### Validate Pattern (file event + runCommand)

Run validation automatically when files change.

```json
{
  "name": "Validate OpenAPI Spec",
  "version": "1.0.0",
  "when": {
    "type": "fileEdited",
    "patterns": ["**/*.yaml", "**/*.yml"]
  },
  "then": {
    "type": "runCommand",
    "command": "npx @redocly/cli lint openapi.yaml"
  }
}
```

### Audit Pattern (postToolUse + askAgent)

Review tool results after execution to catch issues or suggest improvements.

```json
{
  "name": "Code Review After Write",
  "version": "1.0.0",
  "when": {
    "type": "postToolUse",
    "toolTypes": ["write"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Review the code that was just written. Check for security issues, missing error handling, and adherence to project conventions."
  }
}
```

### Bookend Pattern (preTaskExecution + postTaskExecution)

Wrap spec task execution with setup and teardown.

```json
{
  "name": "Task Setup",
  "version": "1.0.0",
  "when": { "type": "preTaskExecution" },
  "then": {
    "type": "askAgent",
    "prompt": "Before starting this task, review the requirements and identify any dependencies or blockers."
  }
}
```

```json
{
  "name": "Task Verification",
  "version": "1.0.0",
  "when": { "type": "postTaskExecution" },
  "then": {
    "type": "runCommand",
    "command": "npm run test && npm run lint"
  }
}
```

## Writing Effective Prompts

When using `askAgent`, the quality of your prompt determines the quality of the hook's behavior. Guidelines:

1. **Be specific about what to check.** "Review this code" is vague. "Check for SQL injection vulnerabilities and missing input validation" is actionable.

2. **State the desired outcome.** "If the command is destructive, warn the user and ask for confirmation" tells the agent exactly what to do.

3. **Include format instructions when needed.** If you want structured output (like the shell-command-explainer hook), describe the format in the prompt.

4. **Use conditional logic.** "If X, do Y. Otherwise, do Z." helps the agent handle different scenarios without separate hooks.

5. **Keep prompts focused.** One hook, one concern. Don't try to check coding standards, security, and performance in a single hook — split them up.

## Managing Hooks

### In the IDE

- View and manage hooks from the **Agent Hooks** section in the Explorer sidebar.
- Use the Command Palette → **Open Kiro Hook UI** to create new hooks visually.
- Toggle hooks on/off by setting `"enabled": false` in the JSON file.

### Programmatically

Hooks are plain JSON files. You can:
- Version them in git alongside your project
- Share them across teams by committing `.kiro/hooks/` to your repo
- Generate them with scripts or templates
- Copy them from a shared collection (like this repository)

## Compatibility

Hooks are a **Kiro IDE** feature. They are not supported by Claude Code, Codex, Cursor, or other tools. When building hooks for this repository, always note:

```
Compatibility: Kiro IDE
```

## Complete Example

Here is a fully-featured hook that demonstrates all available fields:

```json
{
  "name": "Shell Command Explainer",
  "version": "1.0.0",
  "description": "Before executing any shell command, provides a brief explanation of what the command will do and a safety analysis.",
  "enabled": true,
  "when": {
    "type": "preToolUse",
    "toolTypes": ["shell"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Before executing this shell command, provide:\n\n1. A brief explanation of what this command will do.\n2. A safety assessment — is this command safe to auto-approve?\n\nKeep the output concise."
  }
}
```
