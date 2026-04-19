# Documentation Standards

When a source file is created or modified, evaluate whether `README.md` files and `AGENTS.md` (or `CLAUDE.md`) files need to be updated.

## When to Update

Update documentation when a change:

- Adds, removes, or renames a script
- Changes a script's CLI arguments, behavior, or output
- Adds or removes dependencies
- Changes project structure (new directories, new data files, etc.)
- Alters the virtual environment setup

## When NOT to Update

Skip documentation updates when a change:

- Is purely internal (refactoring, bug fixes that don't change behavior or interface)
- Only affects data files, not code
- Is a work-in-progress or temporary file (prefixed with `_`)

## How to Update

- `README.md` files — Conversational tone, aimed at human readers of varying skill levels. Explain what scripts do, how to use them, and any important notes.
- `AGENTS.md` and `CLAUDE.md` files — Direct and concise, optimized for AI coding agents. Focus on structure, inputs/outputs, dependencies, and key behaviors.

Both types of files should stay in sync regarding which scripts and structures are documented, but the writing style differs as described above.

## Markdown Style

Use GitHub-flavored Markdown features when appropriate, including alerts/admonitions like NOTE, TIP, IMPORTANT, WARNING, and CAUTION.

## Documenting Agent Skills

Agent Skills (e.g. `.agents/skills/`) must be documented in the existing skills section or table in `AGENTS.md` and `README.md`. Follow the structure already used by each file rather than requiring a specific heading level or section name.

For each skill, include only:
- The skill name (from the `name` field in the skill's `SKILL.md` front-matter)
- The skill description (from the `description` field in the skill's `SKILL.md` front-matter)

Do not document a skill's internal scripts, usage details, or implementation in `AGENTS.md` or `README.md`. The skill's own `SKILL.md` is the authoritative source for that information. If a skill's scripts are currently documented alongside other repository documentation, replace those entries with a brief skill summary in the existing skills section or table.

Both `AGENTS.md` and `README.md` should list each skill's name and description in their skills section or table. Keep the tone consistent with each file's style — concise and direct in `AGENTS.md`, conversational in `README.md`.

## Important

- Do NOT ask the user whether to update docs. Just evaluate silently and either update or move on.
- If no update is needed, say nothing about it. Do not announce that you checked.
- Keep updates minimal and focused on what actually changed.
