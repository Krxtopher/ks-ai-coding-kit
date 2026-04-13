#!/usr/bin/env python3
"""KS AI Coding Kit installer.

A catalog-driven CLI that installs steering files, hooks, skills,
and prompts into the correct location for your AI coding tool.

Usage:
    python install.py list
    python install.py list --tag safety
    python install.py list --type hook
    python install.py list --tool kiro
    python install.py install ai-memory --dest /path/to/project --tool kiro --mode copy
    python install.py install ai-memory --dest /path/to/project --tool kiro --mode symlink
    python install.py install ai-memory --dest /path/to/project --dry-run --tool kiro --mode copy
    python install.py uninstall ai-memory --dest /path/to/project --tool kiro
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    # Inline pure-Python YAML subset parser for simple catalog files.
    yaml = None  # type: ignore[assignment]

CATALOG_FILE = "catalog.yaml"
SKILL_ENTRY = "SKILL.md"

# Steering injection: tool-specific root files for tools that don't use AGENTS.md.
# Everything not listed here defaults to AGENTS.md.
STEERING_ROOT_OVERRIDES: dict[str, str] = {
    "claude-code": "CLAUDE.md",
}
STEERING_ROOT_DEFAULT = "AGENTS.md"
INJECT_PREFIX = "ks-ai-coding-kit"


# ---------------------------------------------------------------------------
# Minimal YAML parser (stdlib-only fallback)
# ---------------------------------------------------------------------------

def _parse_yaml_minimal(text: str) -> dict:
    """Parse the catalog YAML without PyYAML.

    Handles only the subset used by catalog.yaml: top-level key with a list
    of mappings containing scalar and list values. Not a general-purpose parser.
    """
    import re

    items: list[dict] = []
    current: dict | None = None
    in_targets = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level "items:" key
        if stripped == "items:":
            continue

        indent = len(raw_line) - len(raw_line.lstrip())

        # New list item at indent 2
        if raw_line.lstrip().startswith("- name:") and indent == 2:
            current = {}
            items.append(current)
            in_targets = False
            val = stripped.split(":", 1)[1].strip()
            current["name"] = val
            continue

        if current is None:
            continue

        # Targets sub-mapping
        if stripped == "targets:":
            current["targets"] = {}
            in_targets = True
            continue

        if in_targets and indent >= 6:
            key, _, val = stripped.partition(":")
            val = val.strip()
            if val in ("null", "~", ""):
                current["targets"][key.strip()] = None
            else:
                current["targets"][key.strip()] = val
            continue

        if in_targets and indent < 6:
            in_targets = False

        # Regular key: value
        key, _, val = stripped.lstrip("- ").partition(":")
        val = val.strip()

        # Inline list [a, b, c]
        list_match = re.match(r"^\[(.+)\]$", val)
        if list_match:
            current[key.strip()] = [
                v.strip().strip("'\"") for v in list_match.group(1).split(",")
            ]
        else:
            # Strip surrounding quotes from scalar values.
            if len(val) >= 2 and val[0] in ("'", '"') and val[-1] == val[0]:
                val = val[1:-1]
            current[key.strip()] = val

    return {"items": items}


def load_yaml(path: Path) -> dict:
    """Load YAML from *path*, using PyYAML if available."""
    text = path.read_text()
    if yaml is not None:
        return yaml.safe_load(text)
    return _parse_yaml_minimal(text)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CatalogItem:
    name: str
    type: str
    source: str
    description: str
    tags: list[str] = field(default_factory=list)
    compatibility: list[str] = field(default_factory=list)
    targets: dict[str, Optional[str]] = field(default_factory=dict)
    steering_inject: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> CatalogItem:
        return cls(
            name=data["name"],
            type=data["type"],
            source=data["source"],
            description=data.get("description", ""),
            tags=data.get("tags", []),
            compatibility=data.get("compatibility", []),
            targets=data.get("targets", {}),
        )


def _read_skill_steering_inject(repo_root: Path, source: str) -> Optional[str]:
    """Read the steering-inject value from a skill's SKILL.md metadata."""
    import re as _re

    skill_md = repo_root / source / SKILL_ENTRY
    if not skill_md.exists():
        return None

    text = skill_md.read_text()
    # Extract YAML front-matter between --- delimiters.
    fm_match = _re.match(r"^---\s*\n(.+?)\n---", text, _re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)

    # Try PyYAML first for robust parsing.
    if yaml is not None:
        fm = yaml.safe_load(fm_text)
        if isinstance(fm, dict):
            metadata = fm.get("metadata", {})
            if isinstance(metadata, dict):
                return metadata.get("steering-inject")
        return None

    # Fallback: line-based extraction for steering-inject inside metadata.
    lines = fm_text.splitlines()
    in_metadata = False
    found_key = False
    value_parts: list[str] = []
    key_indent: int = 0

    for raw_line in lines:
        stripped = raw_line.strip()
        indent = len(raw_line) - len(raw_line.lstrip())

        # Detect the metadata: block.
        if stripped == "metadata:" and indent == 0:
            in_metadata = True
            continue

        if not in_metadata:
            continue

        # Left the metadata block (another top-level key).
        if indent == 0 and stripped:
            break

        if found_key:
            # Collecting continuation lines for a block scalar.
            if indent > key_indent and stripped:
                value_parts.append(stripped)
            else:
                break
            continue

        if "steering-inject:" in stripped:
            key_indent = indent
            _, _, val = stripped.partition("steering-inject:")
            val = val.strip().strip("'\"")
            # Block scalar indicator (>, |, >-, |-) — collect following lines.
            if val in (">", "|", ">-", "|-", ""):
                found_key = True
                continue
            return val

    if value_parts:
        return " ".join(value_parts)
    return None


def load_catalog(repo_root: Path) -> list[CatalogItem]:
    """Load and parse the catalog file."""
    catalog_path = repo_root / CATALOG_FILE
    if not catalog_path.exists():
        print(f"Error: catalog file not found at {catalog_path}", file=sys.stderr)
        sys.exit(1)
    raw = load_yaml(catalog_path)
    items: list[CatalogItem] = []
    for data in raw.get("items", []):
        item = CatalogItem.from_dict(data)
        # For skills, read steering-inject from the SKILL.md metadata.
        if item.type == "skill":
            item.steering_inject = _read_skill_steering_inject(repo_root, item.source)
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# Steering injection
# ---------------------------------------------------------------------------

def _steering_root_file(tool: str) -> str:
    """Return the root steering file path for a given tool."""
    return STEERING_ROOT_OVERRIDES.get(tool, STEERING_ROOT_DEFAULT)


def inject_steering(
    dest: Path,
    tool: str,
    item: CatalogItem,
    *,
    dry_run: bool = False,
) -> None:
    """Append steering-inject text to the tool's root steering file."""
    if not item.steering_inject:
        return

    root_file = dest / _steering_root_file(tool)
    marker_open = f"<!-- {INJECT_PREFIX}:{item.name} -->"
    marker_close = f"<!-- /{INJECT_PREFIX}:{item.name} -->"
    block = f"\n{marker_open}\n{item.steering_inject}\n{marker_close}\n"

    # Don't double-inject.
    if root_file.exists() and marker_open in root_file.read_text():
        if dry_run:
            print(f"[dry-run] Steering already present in {root_file}, would skip.")
        return

    if dry_run:
        print(f"[dry-run] Would append to {root_file}:")
        print(f"  {item.steering_inject}")
        return

    root_file.parent.mkdir(parents=True, exist_ok=True)
    with root_file.open("a") as f:
        f.write(block)

    print(f"  ↳ Injected steering into {root_file}")


def remove_steering(
    dest: Path,
    tool: str,
    item: CatalogItem,
    *,
    dry_run: bool = False,
) -> None:
    """Remove the injected steering block from the tool's root steering file."""
    import re as _re

    if not item.steering_inject:
        return

    root_file = dest / _steering_root_file(tool)
    if not root_file.exists():
        return

    content = root_file.read_text()
    marker_open = f"<!-- {INJECT_PREFIX}:{item.name} -->"
    if marker_open not in content:
        return

    if dry_run:
        print(f"[dry-run] Would remove steering block from {root_file}")
        return

    marker_close = f"<!-- /{INJECT_PREFIX}:{item.name} -->"
    pattern = rf"\n?{_re.escape(marker_open)}\n.*?\n{_re.escape(marker_close)}\n?"
    cleaned = _re.sub(pattern, "", content, flags=_re.DOTALL)
    root_file.write_text(cleaned)

    print(f"  ↳ Removed steering from {root_file}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(
    catalog: list[CatalogItem],
    *,
    tag: Optional[str] = None,
    item_type: Optional[str] = None,
    tool: Optional[str] = None,
) -> None:
    """Print a filtered list of catalog items."""
    filtered = catalog
    if tag:
        filtered = [i for i in filtered if tag in i.tags]
    if item_type:
        filtered = [i for i in filtered if i.type == item_type]
    if tool:
        filtered = [i for i in filtered if tool in i.compatibility]

    if not filtered:
        print("No items match the given filters.")
        return

    # Column widths
    name_w = max(len(i.name) for i in filtered)
    type_w = max(len(i.type) for i in filtered)

    print(f"{'Name':<{name_w}}  {'Type':<{type_w}}  {'Tools':<20}  Description")
    print(f"{'─' * name_w}  {'─' * type_w}  {'─' * 20}  {'─' * 40}")
    for item in filtered:
        tools_str = ", ".join(item.compatibility)
        print(f"{item.name:<{name_w}}  {item.type:<{type_w}}  {tools_str:<20}  {item.description}")


def cmd_install(
    item: CatalogItem,
    *,
    repo_root: Path,
    dest: Path,
    tool: str,
    mode: str,
    dry_run: bool = False,
) -> None:
    """Install a single catalog item."""
    target_rel = item.targets.get(tool)
    if target_rel is None:
        print(f"Error: '{item.name}' is not compatible with {tool}.", file=sys.stderr)
        sys.exit(1)

    src = repo_root / item.source
    dst = dest / target_rel

    if not src.exists():
        print(f"Error: source file not found: {src}", file=sys.stderr)
        sys.exit(1)

    verb = "symlink" if mode == "symlink" else "copy"

    if dry_run:
        print(f"[dry-run] Would {verb}:")
        print(f"  {src}")
        print(f"  → {dst}")
        if dst.exists() or dst.is_symlink():
            print(f"  ⚠ Destination already exists and would be overwritten.")
        inject_steering(dest, tool, item, dry_run=True)
        return

    if dst.exists() or dst.is_symlink():
        response = input(f"'{dst}' already exists. Overwrite? [y/N] ").strip().lower()
        if response != "y":
            print("Skipped.")
            return
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)

    if mode == "symlink":
        dst.symlink_to(src.resolve())
    elif src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

    print(f"✓ Installed '{item.name}' ({verb}) → {dst}")

    # Inject steering text into the tool's root steering file if configured.
    inject_steering(dest, tool, item, dry_run=False)


def cmd_uninstall(
    item: CatalogItem,
    *,
    dest: Path,
    tool: str,
    dry_run: bool = False,
) -> None:
    """Remove a previously installed catalog item."""
    target_rel = item.targets.get(tool)
    if target_rel is None:
        print(f"Error: '{item.name}' has no target for {tool}.", file=sys.stderr)
        sys.exit(1)

    dst = dest / target_rel

    if not dst.exists():
        print(f"'{item.name}' is not installed at {dst}.")
        return

    if dry_run:
        print(f"[dry-run] Would remove: {dst}")
        remove_steering(dest, tool, item, dry_run=True)
        return

    if dst.is_symlink() or not dst.is_dir():
        dst.unlink()
    else:
        shutil.rmtree(dst)

    print(f"✓ Uninstalled '{item.name}' (removed {dst})")

    # Remove injected steering text from the tool's root steering file.
    remove_steering(dest, tool, item, dry_run=False)


# ---------------------------------------------------------------------------
# Argument resolution helpers
# ---------------------------------------------------------------------------

def prompt_choice(prompt_text: str, options: list[str]) -> str:
    """Present a numbered menu and return the user's choice."""
    print(prompt_text)
    for i, option in enumerate(options, 1):
        print(f"  {i}) {option}")
    while True:
        try:
            raw = input("Enter choice: ").strip()
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {len(options)}.")


def resolve_tool(args_tool: Optional[str], dest: Path, item: CatalogItem) -> str:
    """Determine the target tool, prompting interactively if not specified."""
    if args_tool:
        return args_tool

    # Only offer tools that the item actually supports.
    compatible = list(item.targets.keys())
    if len(compatible) == 1:
        print(f"Only one compatible tool: {compatible[0]}")
        return compatible[0]

    # If multiple compatible tools, let the user pick.
    return prompt_choice(
        f"Which tool are you installing '{item.name}' for?",
        compatible,
    )


def resolve_mode(args_mode: Optional[str]) -> str:
    """Determine install mode (copy or symlink), prompting if not specified."""
    if args_mode:
        return args_mode
    return prompt_choice(
        "How should the extension be installed?",
        ["copy", "symlink"],
    )


def find_item(catalog: list[CatalogItem], name: str) -> CatalogItem:
    """Look up a catalog item by name."""
    for item in catalog:
        if item.name == name:
            return item
    print(f"Error: '{name}' not found in catalog.", file=sys.stderr)
    print(f"Available items: {', '.join(i.name for i in catalog)}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Install KS AI Coding Kit extensions from the catalog.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    ls = sub.add_parser("list", help="List available extensions")
    ls.add_argument("--tag", help="Filter by tag")
    ls.add_argument("--type", dest="item_type", help="Filter by type (steering, hook, skill, prompt)")
    ls.add_argument("--tool", help="Filter by compatible tool")

    # install
    inst = sub.add_parser("install", help="Install an extension")
    inst.add_argument("name", help="Item name from the catalog")
    inst.add_argument("--dest", required=True, help="Target project directory")
    inst.add_argument("--tool", help="Target tool (prompted if omitted)")
    inst.add_argument("--mode", choices=["copy", "symlink"], help="Install as a copy or symlink (prompted if omitted)")
    inst.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    # uninstall
    uninst = sub.add_parser("uninstall", help="Remove an installed extension")
    uninst.add_argument("name", help="Item name from the catalog")
    uninst.add_argument("--dest", required=True, help="Target project directory")
    uninst.add_argument("--tool", help="Target tool (prompted if omitted)")
    uninst.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    catalog = load_catalog(repo_root)

    if args.command == "list":
        cmd_list(catalog, tag=args.tag, item_type=args.item_type, tool=args.tool)
        return

    dest = Path(args.dest).resolve()
    if not dest.is_dir():
        print(f"Error: destination '{dest}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    item = find_item(catalog, args.name)
    tool = resolve_tool(args.tool, dest, item)

    if args.command == "install":
        mode = resolve_mode(args.mode)
        cmd_install(item, repo_root=repo_root, dest=dest, tool=tool, mode=mode, dry_run=args.dry_run)
    elif args.command == "uninstall":
        cmd_uninstall(item, dest=dest, tool=tool, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
