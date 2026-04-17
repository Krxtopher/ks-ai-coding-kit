# Kiro Steering Files Specification

> Complete reference for building steering files that guide agent behavior in Kiro IDE.

## Overview

A steering file is a Markdown document that provides standing instructions, context, or conventions to the AI agent during a coding session. Steering files live in `.kiro/steering/` inside your workspace and are loaded into the agent's context based on their inclusion mode.

Think of steering files as a persistent system prompt scoped to your project. They're the primary mechanism for telling the agent *how* you want it to work — coding standards, architectural decisions, project-specific knowledge, workflow rules, and anything else that should influence every (or some) interaction.

## File Location and Naming

```
<workspace>/
└── .kiro/
    └── steering/
        ├── python-conventions.md
        ├── api-guidelines.md
        ├── react-patterns.md
        └── ...
```

- Steering files are plain Markdown (`.md`) files.
- They may optionally include YAML front-matter for metadata.
- File names should be descriptive and kebab-cased.
- Kiro watches the `.kiro/steering/` directory and picks up changes automatically.

There is also a **user-level** steering directory at `~/.kiro/steering/` for global rules that apply across all workspaces.

## Front-Matter Schema

The YAML front-matter block is optional. When present, it controls how and when the steering file is loaded.

```yaml
---
name: Python Conventions
description: PEP 8 style, type hints, and project structure standards.
compatibility: Kiro IDE
tags: [python, style, conventions]
inclusion: auto
---
```

### Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | No | string | Human-readable name for the steering file. |
| `description` | No | string | Brief description of what the file covers. |
| `compatibility` | No | string | Which tools this steering file targets (e.g. `Kiro IDE`). |
| `tags` | No | string[] | Tags for categorization and filtering. |
| `inclusion` | No | string | When the file is loaded into context. One of: `auto`, `fileMatch`, `manual`. Defaults to `auto`. |
| `fileMatchPattern` | Conditional | string | Glob pattern for file-based inclusion. Required when `inclusion` is `fileMatch`. |

### Inclusion Modes

Steering files support three inclusion modes that control when their content is loaded into the agent's context:

#### `auto` (default)

The file is **always** included in the agent's context for every interaction. Use this for rules and conventions that should apply universally — coding standards, project structure guidelines, team norms.

```yaml
---
inclusion: auto
---
```

If no front-matter is present, or if `inclusion` is omitted, the file defaults to `auto`.

#### `fileMatch`

The file is included **only when a matching file is read** into context. This is useful for language-specific or framework-specific rules that only matter when the agent is working with relevant files.

Requires the `fileMatchPattern` field, which accepts a glob pattern.

```yaml
---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---
```

Examples of useful `fileMatch` patterns:

| Pattern | Matches |
|---------|---------|
| `**/*.py` | All Python files |
| `**/*.ts` | All TypeScript files |
| `**/*.tsx` | All React TSX files |
| `src/api/**` | Files under the API directory |
| `*.yaml` | YAML files in the workspace root |
| `Dockerfile*` | Dockerfiles |
| `**/*.test.*` | Test files |
| `README*` | README files in any format |

#### `manual`

The file is included **only when the user explicitly references it** using the `#` context key in chat. This is useful for specialized instructions that are only needed occasionally — deployment checklists, migration guides, rarely-used workflows.

```yaml
---
inclusion: manual
---
```

When a steering file has `inclusion: manual`, the user references it in chat like any other context item by typing `#` followed by the file name.

## Body Content

The Markdown body after the front-matter (or the entire file if there's no front-matter) contains the actual instructions. There are no format restrictions — write whatever helps the agent do its job effectively.

### File References

Steering files support references to other files in the workspace using the syntax:

```
#[[file:<relative_file_name>]]
```

This is a lightweight way to pull in additional context without duplicating content. For example, you can reference an OpenAPI spec, a GraphQL schema, or a shared configuration file:

```markdown
When implementing API endpoints, follow the schema defined in:
#[[file:openapi.yaml]]

Database models are defined in:
#[[file:src/models/schema.prisma]]
```

The referenced file's content is included in the agent's context when the steering file is loaded. This keeps steering files focused on instructions while delegating detailed specs to their source-of-truth files.

## Writing Effective Steering Files

### Structure

A well-structured steering file typically includes:

1. **Purpose** — A brief statement of what this file covers and why it exists.
2. **Rules** — Concrete, actionable instructions the agent should follow.
3. **Examples** — Code snippets or patterns that illustrate the rules.
4. **Anti-patterns** — Things to avoid, with explanations of why.

### Guidelines

1. **Be specific and actionable.** "Write good code" is useless. "Use `pathlib.Path` instead of `os.path` for all file system operations" is clear and enforceable.

2. **Use imperative mood.** "Use type hints on all function signatures" rather than "Type hints should be used."

3. **Provide examples.** Show the agent what correct code looks like. A short code block is worth a paragraph of explanation.

4. **Keep files focused.** One steering file per concern. Don't mix Python conventions with deployment procedures — split them into separate files.

5. **Prefer positive instructions over prohibitions.** "Use `logging` for all output" is better than "Don't use `print()`." Include both when the anti-pattern is common.

6. **Consider token budget.** Every `auto` steering file is loaded into every conversation. Keep them concise. Move detailed reference material to `manual` or `fileMatch` files.

7. **Use Markdown formatting.** Headers, lists, code blocks, and tables all help the agent parse and apply your instructions. Avoid walls of unstructured text.

## Examples

### Always-On Coding Standards

```markdown
---
name: Python Conventions
description: PEP 8 style, type hints, and project structure standards.
inclusion: auto
---

# Python Conventions

## Style

- Follow PEP 8.
- Use type hints for all function signatures and return types.
- Prefer f-strings over `.format()` or `%` formatting.
- Use `pathlib.Path` over `os.path` for file system operations.

## Structure

- One responsibility per function.
- Use `if __name__ == "__main__":` guards in scripts.
- Prefer dataclasses or Pydantic models over raw dicts for structured data.

## Error Handling

- Catch specific exceptions, never bare `except:`.
- Use `logging` over `print()` for anything beyond quick debugging.
```

### File-Matched React Guidelines

```markdown
---
name: React Patterns
description: Component patterns and hooks conventions for React files.
inclusion: fileMatch
fileMatchPattern: "**/*.tsx"
---

# React Patterns

## Components

- Use functional components with hooks. No class components.
- Export components as named exports, not default exports.
- Co-locate styles with components using CSS modules.

## Hooks

- Prefix custom hooks with `use`.
- Keep hooks focused — one concern per hook.
- Memoize expensive computations with `useMemo`.
- Memoize callbacks passed to child components with `useCallback`.

## Accessibility

- All interactive elements must have accessible labels.
- Use semantic HTML elements (`button`, `nav`, `main`) over generic `div`.
- Include `aria-` attributes where semantic HTML is insufficient.
```

### Manual Deployment Checklist

```markdown
---
name: Deployment Checklist
description: Pre-deployment verification steps for production releases.
inclusion: manual
---

# Deployment Checklist

Before deploying to production, verify:

1. All tests pass: `npm run test`
2. No lint errors: `npm run lint`
3. Build succeeds: `npm run build`
4. Environment variables are set in the target environment
5. Database migrations have been applied
6. Changelog has been updated
7. Version has been bumped in `package.json`
```

### Steering with File References

```markdown
---
name: API Implementation Guide
description: Guidelines for implementing API endpoints based on the OpenAPI spec.
inclusion: fileMatch
fileMatchPattern: "src/api/**"
---

# API Implementation Guide

All API endpoints must conform to the schema defined in:
#[[file:openapi.yaml]]

## Conventions

- Use the controller → service → repository pattern.
- Validate request bodies against the OpenAPI schema.
- Return standard error responses as defined in the spec's `components/schemas/Error`.
- Log all 5xx errors with full request context.
```

## Workspace vs. User-Level Steering

| Location | Scope | Use Case |
|----------|-------|----------|
| `.kiro/steering/` | Workspace | Project-specific rules shared with the team via version control. |
| `~/.kiro/steering/` | User (global) | Personal preferences that apply across all projects. |

Workspace-level steering takes precedence over user-level steering when there are conflicts. This means a team can enforce project standards that override individual preferences.

### Team Sharing

Since `.kiro/steering/` lives inside the workspace, you can commit it to version control. This gives the whole team consistent agent behavior:

```
.kiro/
└── steering/
    ├── coding-standards.md    # Team coding conventions
    ├── architecture.md        # Project architecture decisions
    └── testing.md             # Testing requirements
```

Add `.kiro/steering/` to your repository and new team members get the same agent behavior out of the box.

## Compatibility

Steering files are a **Kiro IDE** feature. Other tools have analogous concepts:

| Tool | Equivalent |
|------|-----------|
| Kiro IDE | `.kiro/steering/*.md` |
| Claude Code | `CLAUDE.md` in project root |
| Codex | `AGENTS.md` in project root |
| Cursor | `.cursor/rules/*.md` or `.cursorrules` |

When building steering files for this repository, always note:

```
Compatibility: Kiro IDE
```

If a steering file's content is broadly applicable, consider also creating equivalent files for other tools under `agent-instructions/`.

## Relationship to Other Kiro Features

### Steering vs. Skills

- **Steering files** provide passive instructions — they tell the agent *how* to behave but don't give it new capabilities.
- **Skills** provide active capabilities — they teach the agent *how to do* something specific, with scripts, references, and structured workflows.

Use steering for conventions and context. Use skills for complex, multi-step capabilities.

### Steering vs. Hooks

- **Steering files** are loaded into context and influence the agent's behavior across the conversation.
- **Hooks** are event-driven automations that trigger specific actions at specific moments.

Use steering for standing rules. Use hooks for automated reactions to events.

### Steering + Specs

Kiro specs (structured feature documents) can reference steering files via `#[[file:...]]` syntax. This means your spec tasks automatically inherit the conventions defined in your steering files.
