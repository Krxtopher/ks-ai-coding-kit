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
| `tts-narrator/` | Speaks status updates aloud using Amazon Polly (see below) | Multiple |

## TTS Narrator

A set of hooks that provide verbal feedback during Kiro sessions using Amazon Polly text-to-speech. Audio plays in the background via macOS `afplay` so it never blocks agent execution.

### Hooks

| Hook File | Event | What It Says |
|-----------|-------|--------------|
| `tts-session-start.kiro.hook` | `sessionStart` | Greeting when a session begins |
| `tts-pre-shell.kiro.hook` | `preToolUse` (shell) | Names the command about to run |
| `tts-post-shell.kiro.hook` | `postToolUse` (shell) | Confirms completion or flags errors |
| `tts-post-task.kiro.hook` | `postTaskExecution` | Announces a spec task finished |
| `tts-agent-stop.kiro.hook` | `agentStop` | Wrap-up when the agent finishes |

### Requirements

- **macOS** (uses `afplay` for audio playback)
- **Python 3.10+** with `boto3`
- **AWS credentials** with access to Amazon Polly (`polly:SynthesizeSpeech`)

Install Python dependencies:

```bash
pip install -r hooks/tts-narrator/requirements.txt
```

### Installation

Copy the entire `tts-narrator/` directory into your workspace's `.kiro/hooks/`:

```bash
cp -r hooks/tts-narrator /path/to/your/project/.kiro/hooks/
```

### Configuration

Edit `speak.py` to change voice or engine:

| Variable | Default | Options |
|----------|---------|---------|
| `VOICE_ID` | `Matthew` | Any Polly voice (e.g., `Joanna`, `Ruth`, `Stephen`) |
| `ENGINE` | `neural` | `neural`, `standard`, `generative` |

### Disabling Individual Hooks

Set `"enabled": false` in any hook file to silence that trigger without removing it.
