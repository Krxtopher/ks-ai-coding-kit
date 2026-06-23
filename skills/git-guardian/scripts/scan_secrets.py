#!/usr/bin/env python3
"""Scan files for potential secrets and credentials.

Usage:
    # Scan staged files (default)
    python scan_secrets.py

    # Scan specific files
    python scan_secrets.py file1.py file2.env

    # Scan a directory recursively
    python scan_secrets.py --dir src/

Output:
    JSON array of findings, each with:
      - file: path to the file
      - line: line number (1-indexed)
      - pattern: which pattern matched
      - context: the line content with the secret value redacted
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class Finding(NamedTuple):
    file: str
    line: int
    pattern: str
    context: str


# Each pattern: (name, compiled regex)
# These match common credential formats. The goal is useful signal with
# minimal false positives — we'd rather miss an unusual format than flood
# the user with noise.
PATTERNS: list[tuple[str, re.Pattern]] = [
    # AWS
    ("AWS Access Key ID", re.compile(r"(?<![A-Z0-9])(AKIA[0-9A-Z]{16})(?![A-Z0-9])")),
    ("AWS Secret Access Key", re.compile(
        r"""(?i)(?:aws_secret_access_key|aws_secret_key|secret_access_key)\s*[=:]\s*['"]?([A-Za-z0-9/+=]{40})['"]?"""
    )),
    ("AWS Session Token", re.compile(
        r"""(?i)(?:aws_session_token|session_token)\s*[=:]\s*['"]?([A-Za-z0-9/+=]{100,})['"]?"""
    )),
    ("AWS MWS Key", re.compile(r"(?i)amzn\.mws\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")),
    # Generic cloud / API tokens
    ("GitHub Token", re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}")),
    ("GitLab Token", re.compile(r"glpat-[A-Za-z0-9\-_]{20,}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}")),
    ("OpenAI API Key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("Anthropic API Key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("Generic Bearer Token", re.compile(
        r"""(?i)(?:bearer|authorization)\s*[=:]\s*['"]?Bearer\s+[A-Za-z0-9\-_.~+/]+=*['"]?"""
    )),
    # Private keys
    ("Private Key", re.compile(r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH|PGP)?\s*PRIVATE KEY-----")),
    # Connection strings with passwords
    ("Connection String with Password", re.compile(
        r"""(?i)(?:mysql|postgres|postgresql|mongodb|redis|amqp|mssql):\/\/[^:]+:[^@\s]+@"""
    )),
    # Generic high-entropy assignments to suspicious variable names
    ("Password Assignment", re.compile(
        r"""(?i)(?:password|passwd|pwd|secret|api_key|apikey|api_secret|access_token|auth_token)\s*[=:]\s*['"][^'"]{8,}['"]"""
    )),
    # .env style secrets
    ("Env Secret Assignment", re.compile(
        r"""(?i)^(?:export\s+)?(?:AWS_SECRET_ACCESS_KEY|DATABASE_URL|SECRET_KEY|PRIVATE_KEY|API_KEY|AUTH_TOKEN)\s*=\s*\S+"""
    )),
]

# Files to always skip (binary, lock files, etc.)
SKIP_EXTENSIONS = frozenset([
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".lock", ".sum",
    ".pyc", ".pyo", ".class",
])

SKIP_DIRS = frozenset([
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache",
])


def get_staged_files() -> list[str]:
    """Return list of staged file paths via git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, check=True,
        )
        return [f for f in result.stdout.strip().splitlines() if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def should_skip(path: Path) -> bool:
    """Check if a file should be skipped based on extension or directory."""
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def redact(line: str, match: re.Match) -> str:
    """Replace the matched secret with a redacted placeholder."""
    start, end = match.span()
    secret_len = end - start
    # Show first 4 chars if long enough, redact the rest
    if secret_len > 8:
        visible = line[start:start + 4]
        return line[:start] + visible + "*" * (secret_len - 4) + line[end:]
    return line[:start] + "*" * secret_len + line[end:]


def scan_file(filepath: Path) -> list[Finding]:
    """Scan a single file for secret patterns."""
    if should_skip(filepath):
        return []

    findings: list[Finding] = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        return []

    for line_num, line in enumerate(text.splitlines(), start=1):
        # Skip comments that look like documentation/examples
        stripped = line.strip()
        if stripped.startswith("#") and ("example" in stripped.lower() or "placeholder" in stripped.lower()):
            continue

        for pattern_name, pattern in PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(Finding(
                    file=str(filepath),
                    line=line_num,
                    pattern=pattern_name,
                    context=redact(line.strip(), pattern.search(line.strip())),
                ))
                break  # One finding per line is enough

    return findings


def collect_files(directory: Path) -> list[Path]:
    """Recursively collect scannable files from a directory."""
    files: list[Path] = []
    for item in directory.rglob("*"):
        if item.is_file() and not should_skip(item):
            files.append(item)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan files for potential secrets")
    parser.add_argument("files", nargs="*", help="Files to scan (default: git staged files)")
    parser.add_argument("--dir", type=str, help="Scan a directory recursively")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    files_to_scan: list[Path] = []

    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"Error: {args.dir} is not a directory", file=sys.stderr)
            sys.exit(1)
        files_to_scan = collect_files(dir_path)
    elif args.files:
        files_to_scan = [Path(f) for f in args.files if Path(f).is_file()]
    else:
        # Default: scan staged files
        staged = get_staged_files()
        if not staged:
            print("[]")
            return
        files_to_scan = [Path(f) for f in staged if Path(f).is_file()]

    all_findings: list[dict] = []
    for filepath in files_to_scan:
        for finding in scan_file(filepath):
            all_findings.append({
                "file": finding.file,
                "line": finding.line,
                "pattern": finding.pattern,
                "context": finding.context,
            })

    indent = 2 if args.pretty else None
    print(json.dumps(all_findings, indent=indent))

    # Exit with non-zero status if findings exist
    if all_findings:
        sys.exit(1)


if __name__ == "__main__":
    main()
