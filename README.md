# KS AI Coding Kit

Reusable extensions for AI coding tools — skills, hooks, and agent instructions that work across [Kiro](https://kiro.dev), [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex](https://openai.com/index/introducing-codex/), [Cursor](https://www.cursor.com/), and other AI-assisted editors.

## What's Included

### Skills

| | Name | Description |
|---|------|-------------|
| <img src="docs/icons/brain.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="brain icon" /> | [agent-memory](skills/agent-memory/SKILL.md) | Persistent memory across conversations. Supports project-scoped and user-scoped memories. |
| <img src="docs/icons/hammer.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="hammer icon" /> | [agent-skill-builder](skills/agent-skill-builder/SKILL.md) | Guides you through creating new Agent Skills, with the full spec bundled for reference. |
| <img src="docs/icons/eye.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="eye icon" /> | [bedrock-vision](skills/bedrock-vision/SKILL.md) | Analyze images using Bedrock vision models. Returns AI description plus technical metadata. |
| <img src="docs/icons/clock.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="clock icon" /> | [current-time](skills/current-time/SKILL.md) | Looks up the current date and time in local and UTC, accurate to the second |
| <img src="docs/icons/file-text.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="file-text icon" /> | [doc-convert](skills/doc-convert/SKILL.md) | Document conversion via pandoc with a styled Word template |
| <img src="docs/icons/shield-check.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="shield-check icon" /> | [git-guardian](skills/git-guardian/SKILL.md) | Git commit and branching guardian — scans for secrets, large files, archives, and notebook output before committing |
| <img src="docs/icons/workflow.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="workflow icon" /> | [mermaid-diagram](skills/mermaid-diagram/SKILL.md) | Generates static PNG images from Mermaid diagram definitions using the local Mermaid CLI |
| <img src="docs/icons/audio-lines.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="audio-lines icon" /> | [narrator-kokoro](skills/narrator-kokoro/SKILL.md) | Text-to-speech narrator using Kokoro (local ONNX model) — fast, fully offline speech synthesis with zero API keys or cloud dependencies |
| <img src="docs/icons/audio-lines.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="audio-lines icon" /> | [narrator-elevenlabs](skills/narrator-elevenlabs/SKILL.md) | Text-to-speech narrator using ElevenLabs streaming API — high-quality cloud voices with low-latency playback |
| <img src="docs/icons/audio-lines.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="audio-lines icon" /> | [narrator-polly](skills/narrator-polly/SKILL.md) | Text-to-speech narrator using Amazon Polly generative engine — zero API key setup, uses AWS credentials, low-latency streaming |
| <img src="docs/icons/graduation-cap.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="graduation-cap icon" /> | [tutorial-jupyter-notebook](skills/tutorial-jupyter-notebook/SKILL.md) | Guide for creating high-quality educational Jupyter Notebooks that teach workflows, patterns, and technical concepts |

### Hooks

| | Name | Description | Compatibility |
|---|------|-------------|---------------|
| <img src="docs/icons/terminal.svg" width="31" height="31" style="min-width:31px;max-width:31px" alt="terminal icon" /> | [shell-command-explainer](hooks/shell-command-explainer.kiro.hook) | Explains shell commands before execution with safety analysis | Kiro only |

### Agent Instructions

Reusable instruction sets — coding standards, project context, workflows — designed to be appended to your project's `AGENTS.md`. All tools supported by this kit read this file natively.

## Quick Start

### Installing Skills

Skills are installed with [`npx skills`](https://www.npmjs.com/package/skills):

```bash
# Install a skill from GitHub (interactive — prompts for skill and agent)
npx skills add Krxtopher/ks-ai-coding-kit

# Install a specific skill for a specific agent
npx skills add Krxtopher/ks-ai-coding-kit --skill agent-memory --agent kiro-cli -y

# Install all skills for all agents
npx skills add Krxtopher/ks-ai-coding-kit --all

# Install from a local clone
npx skills add ./skills --skill agent-memory --agent kiro-cli -y
```

Other useful commands:

```bash
npx skills list              # see what's installed
npx skills update -y         # update all installed skills
npx skills remove agent-memory --agent kiro-cli -y
```

Agent names: `kiro-cli`, `claude-code`, `codex`, `cursor`. Use `*` for all agents.

### Installing Hooks & Agent Instructions

Non-skill extensions (hooks and agent instructions) use the bundled `install.py`:

```bash
python install.py list
python install.py install shell-command-explainer --dest ~/my-project --tool kiro
python install.py uninstall shell-command-explainer --dest ~/my-project --tool kiro
```

## How It Works

**Skills** follow the open [Agent Skills](https://agentskills.io/) standard. Each skill lives in its own directory under `skills/` with a `SKILL.md` entry point. The `npx skills` CLI handles placement into the correct tool-specific path (`.kiro/skills/`, `.claude/skills/`, `.agents/skills/`) and manages a lock file for updates.

**Hooks and agent instructions** use `install.py`, which reads `catalog.yaml` and copies files to the right location for your chosen tool.

<details>
<summary>Manual install paths by tool</summary>

| Content Type | Kiro | Claude Code | Codex / Cursor |
|-------------|------|-------------|----------------|
| Skills | `.kiro/skills/<name>` | `.claude/skills/<name>` | `.agents/skills/<name>` |
| Hooks | `.kiro/hooks/<name>` | — | — |
| Instructions | `AGENTS.md` | `CLAUDE.md` or `AGENTS.md` | `AGENTS.md` |

</details>

## Concepts

New to AI coding assistants? Here's a quick glossary:

- **Agent instructions** — Markdown files that act as a persistent system prompt for your project. Different tools call them different things (steering files, rules, project instructions), but the idea is the same.
- **Skills** — Multi-file packages that teach the agent a specific capability, following the open [Agent Skills](https://agentskills.io/home) standard. Each includes a `SKILL.md` entry point with metadata and instructions, plus optional scripts and assets.
- **Hooks** — Event-driven automations (Kiro only). A hook listens for an IDE event and triggers a shell command or agent prompt in response.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Short version: add your skill under `skills/` with a `SKILL.md`, include a Compatibility note, and open a PR. Non-skill extensions (hooks, instructions) also need a `catalog.yaml` entry.

## License

See [LICENSE](LICENSE) for details.

---

Icons by [Lucide](https://lucide.dev/) — MIT licensed.
