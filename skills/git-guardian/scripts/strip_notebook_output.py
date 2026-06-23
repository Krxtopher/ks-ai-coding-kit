#!/usr/bin/env python3
"""Strip cell outputs from Jupyter Notebook (.ipynb) files.

Usage:
    # Check staged .ipynb files for cell output (report only)
    python strip_notebook_output.py --check

    # Strip output from specific notebooks
    python strip_notebook_output.py notebook.ipynb analysis.ipynb

    # Strip output from all staged .ipynb files
    python strip_notebook_output.py --staged

Output:
    --check mode: JSON array of notebooks that contain cell output, with
    per-cell details (cell index, output type, output size estimate).

    Strip mode: modifies files in-place, removing cell outputs and
    execution counts. Prints a summary of what was cleaned.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_staged_notebooks() -> list[str]:
    """Return list of staged .ipynb file paths via git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, check=True,
        )
        return [
            f for f in result.stdout.strip().splitlines()
            if f.endswith(".ipynb")
        ]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def load_notebook(path: Path) -> dict[str, Any] | None:
    """Load and parse a notebook file. Returns None on failure."""
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: could not read {path}: {e}", file=sys.stderr)
        return None


def cell_has_output(cell: dict[str, Any]) -> bool:
    """Check if a notebook cell has any output or execution count."""
    if cell.get("cell_type") != "code":
        return False
    outputs = cell.get("outputs", [])
    execution_count = cell.get("execution_count")
    return bool(outputs) or execution_count is not None


def estimate_output_size(cell: dict[str, Any]) -> int:
    """Rough estimate of output size in characters."""
    outputs = cell.get("outputs", [])
    size = 0
    for output in outputs:
        # Text output
        if "text" in output:
            text = output["text"]
            if isinstance(text, list):
                size += sum(len(line) for line in text)
            else:
                size += len(str(text))
        # Data output (display_data, execute_result)
        if "data" in output:
            for mime_type, content in output["data"].items():
                if isinstance(content, list):
                    size += sum(len(line) for line in content)
                else:
                    size += len(str(content))
    return size


def check_notebooks(paths: list[Path]) -> list[dict[str, Any]]:
    """Check notebooks for cell output. Returns findings."""
    findings: list[dict[str, Any]] = []

    for path in paths:
        notebook = load_notebook(path)
        if notebook is None:
            continue

        cells = notebook.get("cells", [])
        cells_with_output: list[dict[str, Any]] = []

        for idx, cell in enumerate(cells):
            if cell_has_output(cell):
                output_types = set()
                for output in cell.get("outputs", []):
                    output_types.add(output.get("output_type", "unknown"))
                cells_with_output.append({
                    "cell_index": idx,
                    "output_types": sorted(output_types),
                    "output_size_chars": estimate_output_size(cell),
                })

        if cells_with_output:
            findings.append({
                "file": str(path),
                "cells_with_output": len(cells_with_output),
                "total_cells": len(cells),
                "details": cells_with_output,
            })

    return findings


def strip_notebook(path: Path) -> dict[str, Any]:
    """Strip outputs from a notebook file in-place. Returns a summary."""
    notebook = load_notebook(path)
    if notebook is None:
        return {"file": str(path), "error": "could not read file"}

    cells = notebook.get("cells", [])
    cells_cleaned = 0

    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        if cell_has_output(cell):
            cell["outputs"] = []
            cell["execution_count"] = None
            cells_cleaned += 1

    if cells_cleaned > 0:
        # Write back with consistent formatting
        text = json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"
        path.write_text(text, encoding="utf-8")

    return {
        "file": str(path),
        "cells_cleaned": cells_cleaned,
        "total_code_cells": sum(1 for c in cells if c.get("cell_type") == "code"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check or strip cell outputs from Jupyter notebooks"
    )
    parser.add_argument(
        "files", nargs="*",
        help="Notebook files to strip (default: use --staged or --check)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Report notebooks with output (don't modify files)",
    )
    parser.add_argument(
        "--staged", action="store_true",
        help="Target staged .ipynb files",
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    # Determine target files
    if args.files:
        paths = [Path(f) for f in args.files if f.endswith(".ipynb") and Path(f).is_file()]
    elif args.staged:
        staged = get_staged_notebooks()
        paths = [Path(f) for f in staged if Path(f).is_file()]
    elif args.check:
        # --check with no files defaults to staged
        staged = get_staged_notebooks()
        paths = [Path(f) for f in staged if Path(f).is_file()]
    else:
        parser.print_help()
        sys.exit(1)

    if not paths:
        if args.check:
            print("[]")
        else:
            print("No .ipynb files found to process.", file=sys.stderr)
        return

    indent = 2 if args.pretty else None

    if args.check:
        findings = check_notebooks(paths)
        print(json.dumps(findings, indent=indent))
        if findings:
            sys.exit(1)
    else:
        results = [strip_notebook(p) for p in paths]
        print(json.dumps(results, indent=indent))


if __name__ == "__main__":
    main()
