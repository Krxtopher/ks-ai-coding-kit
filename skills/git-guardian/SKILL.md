---
name: git-guardian
description: >
  Enforces Git best practices. Whenever the user wants to perform Git tasks, activate the "git-guardian" skill.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: "1.0"
---

# Git Guardian

This skill provides git safety and hygiene checks. Whenever the user is working with git — committing, staging, branching, or preparing changes — apply the checks and practices below. The goal is to catch problems before they become permanent history.

## Core Principles

1. **Every commit is permanent.** Secrets, large binaries, and sensitive data are extremely difficult to fully remove from git history once pushed. Prevention is far cheaper than remediation.
2. **Commits tell a story.** Each commit should represent one coherent change that a future reader can understand from its message alone.
3. **Ask, don't assume.** When something looks wrong, flag it to the user rather than silently fixing or ignoring it. The user always has final say.

---

## Pre-Commit Checks

Before staging or committing changes, scan the working tree and staged files for the following issues. Report findings to the user clearly and wait for their decision.

### Secrets and Sensitive Data

Run the bundled scanner script to get a deterministic first pass. The location of the script will depend on where the user installed the skill, so check both in the workspace and `~/.<coding-agent-id>/skills/git-guardian/`

```bash
python <skill-path>/scripts/scan_secrets.py
```

This scans staged files by default and outputs JSON findings with redacted context. You can also target specific files or directories:

```bash
python <skill-path>/scripts/scan_secrets.py --dir src/
python <skill-path>/scripts/scan_secrets.py config.py deploy.sh
```

Beyond what the script catches, also watch for these patterns manually — especially in diffs and new files:

**AWS-specific patterns** (common in cloud development):
- IAM Access Key IDs — always start with `AKIA` followed by 16 uppercase alphanumeric characters
- IAM Secret Access Keys — 40-character base64 strings, often assigned to `aws_secret_access_key`
- Session tokens — long base64 strings (typically 300+ chars), assigned to `aws_session_token`
- MWS tokens — format `amzn.mws.<uuid>`
- Pre-signed S3 URLs containing `X-Amz-Credential` and `X-Amz-Signature` parameters
- CloudFormation/SAM templates with hard-coded `SecretKey`, `Password`, or `AccessKey` values in Parameters defaults or Resources
- RDS/Redshift master passwords in plaintext (in Terraform, CDK, or CF templates)
- Boto3 client calls with hard-coded `aws_access_key_id` / `aws_secret_access_key` kwargs

**General patterns:**
- API keys and tokens (prefixed with `sk-`, `ghp_`, `gho_`, `glpat-`, `xoxb-`, `Bearer`)
- Private keys (`-----BEGIN.*PRIVATE KEY-----`)
- Connection strings with embedded passwords (`postgres://user:pass@host`)
- `.env` files or files named `credentials`, `secrets`, `.secret`, `.password`
- GCP service account JSON files (contain `"private_key"`)
- Hard-coded passwords in source (assignments to variables named `password`, `secret`, `api_key`, etc.)

When you detect a potential secret, alert the user immediately. Explain what you found and where. Never include the actual secret value in your output — reference it by location (file and line) and pattern type.

### Large Files

Flag files that are unusually large relative to the rest of the repository. Binary files, media assets, datasets, database dumps, and log files are common offenders.

Consider context: a 2 MB image in a documentation repo might be fine, but a 200 MB video almost certainly shouldn't be committed. Use your judgment based on what the repository contains and what the file is.

When flagging a large file, explain:
- What the file is and how large it is
- Whether it looks like something that belongs in version control
- Alternatives if it doesn't (Git LFS, external storage, a download script)

### ZIP and Archive Files

ZIP files, tarballs, and other archives deserve special scrutiny. They often contain:
- Bundled dependencies that should be installed via a package manager
- Build artifacts that can be regenerated
- Large binary content that inflates repository size
- Nested secrets or sensitive data that's harder to scan

When you encounter an archive file being staged:
- Alert the user that a ZIP/archive is about to be committed
- Ask what it contains and whether it belongs in the repo
- Suggest alternatives (package manager, build step, Git LFS, `.gitignore`)

### Jupyter Notebook Cell Output

When `.ipynb` files are staged or about to be committed, check whether they contain cell output. Notebook outputs (rendered tables, images, tracebacks, print statements, execution counts) often bloat repositories and can leak sensitive data (e.g. DataFrame previews with PII, credentials in stack traces, or large base64-encoded images).

Run the bundled check script to detect notebooks with output:

```bash
python <skill-path>/scripts/strip_notebook_output.py --check
```

If the script reports notebooks containing output, **do not assume the user wants to commit it**. Instead:

1. Tell the user which notebooks have cell output and summarize the scope (number of cells, approximate size).
2. Ask the user: *"These notebooks contain cell output. Would you like to commit the output, or strip it before committing?"*
3. If the user chooses to **strip output**, run the strip command on the affected files:

```bash
python <skill-path>/scripts/strip_notebook_output.py <file1.ipynb> [file2.ipynb ...]
```

This removes all cell outputs and execution counts in-place. After stripping, re-stage the cleaned files before committing:

```bash
git add <file1.ipynb> [file2.ipynb ...]
```

4. If the user chooses to **keep the output**, proceed normally — no modification needed.

> **Note:** The `--staged` flag targets only notebooks currently staged in git. You can also pass specific file paths directly.

---

### Files That Probably Shouldn't Be Tracked

Watch for files and directories that are commonly gitignored but aren't:

- `node_modules/`, `__pycache__/`, `.venv/`, `venv/`, `env/`
- Build output: `dist/`, `build/`, `target/`, `out/`, `.next/`
- IDE/editor files: `.idea/`, `.vscode/settings.json` (not `.vscode/extensions.json`), `*.swp`, `*.swo`, `.DS_Store`, `Thumbs.db`
- OS files: `.DS_Store`, `Thumbs.db`, `Desktop.ini`
- Dependency lock files in contexts where they shouldn't be committed (varies by ecosystem)
- Log files: `*.log`, `npm-debug.log*`
- Coverage/test output: `coverage/`, `.nyc_output/`, `htmlcov/`

For language- or framework-specific patterns beyond these common ones, consult GitHub's gitignore templates at https://github.com/github/gitignore — it covers most ecosystems (Python, Node, Rust, Go, Java, Unity, etc.) and is community-maintained.

When you identify files that should be ignored, suggest adding them to `.gitignore`. Always confirm with the user before modifying `.gitignore` — they may have a reason for tracking something.

---

## Commit Hygiene

### Atomic Commits

Each commit should contain exactly one logical change. Signs that a commit should be split:

- Changes span unrelated files or features
- The commit message needs "and" to describe what it does
- A bug fix is mixed with a feature addition
- Formatting changes are mixed with behavioral changes

When you notice this, suggest splitting the work into multiple commits and explain the groupings you'd recommend.

### Conventional Commit Messages

Format commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) standard:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `style`

**Rules:**
- Subject line in imperative mood ("add feature" not "added feature")
- Subject line under 72 characters
- No period at the end of the subject line
- Body wraps at 72 characters
- Body explains *what* and *why*, not *how*

**Examples:**

```
feat(auth): add OAuth2 login flow

Implements Google and GitHub OAuth providers using passport.js.
Tokens are stored in the session with a 24h expiry.

Closes #142
```

```
fix(api): handle null response from payment gateway

The gateway occasionally returns null on timeout instead of an error
object. This caused an unhandled TypeError in the response parser.
```

### Staging Intentionally

Prefer staging specific files over `git add .` or `git add -A`. When the user asks to commit "everything" or uses a broad staging command, review what's being staged and flag anything that looks unintentional:

- Unrelated changes that should be a separate commit
- Generated files or build artifacts
- Temporary/scratch files (often prefixed with `_` or named `temp`, `test`, `scratch`)

---

## Branching

### Branch Naming

Keep branch names short, lowercase, and hyphenated. Good patterns:

- `feat/oauth-login`
- `fix/null-payment-response`
- `docs/api-reference`
- `chore/update-deps`

Avoid:
- Spaces or special characters
- Very long descriptive names
- Names without a type prefix (when working in a team context)

### Working Branch Safety

Never commit directly to `main`, `master`, or `mainline` unless the user explicitly asks to. If the user is on a protected branch and asks to commit, suggest creating a working branch first.

---

## How to Report Issues

When you find problems, present them clearly and concisely. Group related issues together. For each issue:

1. State what you found (file, line if relevant)
2. Explain why it's a concern
3. Suggest a remedy
4. Wait for the user's decision

Don't block the user from proceeding if they explicitly acknowledge a risk and want to continue. Your job is to inform, not to gatekeep.

---

## What This Skill Does NOT Do

- It does not run `git` commands autonomously without user intent
- It does not modify `.gitignore` without confirmation
- It does not enforce rules the user has explicitly overridden
- It does not scan the entire git history — only the current working tree and staged changes
