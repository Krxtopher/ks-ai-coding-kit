# Agent Skills

Reusable agent skills — packaged capabilities that extend what your AI coding assistant can do.

## What Are Skills?

Skills are multi-file packages that define a specific capability for an AI coding agent. Each skill lives in its own directory and includes a `SKILL.md` entry point that describes the skill's purpose, inputs, and behavior. Skills follow the [Agent Skills open standard](https://agentskills.io/) and work across compatible tools.

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
| `agent-memory/` | Persistent AI memory system with project-scoped and user-scoped memory files for retaining context across conversations |
| `current-time/` | Looks up the current date and time, accurate to the second, in both local time and UTC |
| `doc-convert/` | Convert documents between formats using pandoc — ships with a styled Word reference template for polished Markdown-to-DOCX output |
| `image-describe/` | Analyze images from the workspace by extracting technical metadata and generating AI-powered descriptions via Amazon Bedrock |

## Usage Examples

### agent-memory

> Remember that we decided to use DynamoDB for session storage instead of Redis.

The agent logs the decision to `.agent-memory/project/insights.md` and recalls it in future conversations without being asked.

> Where did we leave off last time?

The agent reads its memory files and summarizes the most recent tasks, decisions, and conversation topics from prior sessions.

### current-time

> My ECS deployment seems stuck. How long has it been running?

The agent checks the current time, compares it to the deployment's start timestamp from the terminal output or logs, and tells the user the elapsed duration.

### doc-convert

> Convert `docs/design-proposal.md` to a Word document.

The agent runs pandoc with the bundled reference template and Lua filter, then fixes list indentation — producing a styled `.docx` ready to share.

### image-describe

> Describe this image and extract all of its text. `test-assets/artemis-sls-infographic.jpg`

The agent extracts image metadata (dimensions, file size, format) and sends the image to a Bedrock vision model, returning a detailed description and full text transcription.
