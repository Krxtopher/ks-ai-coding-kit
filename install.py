#!/usr/bin/env python3
"""KS AI Coding Kit installer.

A catalog-driven CLI that installs agent instructions, hooks, skills,
and other extensions into the correct location for your AI coding tool.

Usage:
    python install.py list
    python install.py list --type hook
    python install.py list --tool kiro
    python install.py install agent-memory --dest /path/to/project --tool kiro
    python install.py install agent-memory --dest /path/to/project --dry-run --tool kiro
    python install.py uninstall agent-memory --dest /path/to/project --tool kiro
    python install.py sync
    python install.py sync agent-memory
    python install.py sync --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
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
MANIFEST_FILE = ".install-manifest.json"
SKILL_ENTRY = "SKILL.md"

# Steering injection: all tools use AGENTS.md as the root steering file.
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
                # Check for inline mapping: { file: ..., mode: ... }
                if val.startswith("{") and val.endswith("}"):
                    inner = val[1:-1].strip()
                    mapping: dict[str, str] = {}
                    for pair in inner.split(","):
                        pair = pair.strip()
                        if ":" in pair:
                            mk, _, mv = pair.partition(":")
                            mapping[mk.strip()] = mv.strip().strip("'\"")
                    current["targets"][key.strip()] = mapping
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
class TargetSpec:
    """Resolved install target for a single tool.

    A target can be specified in the catalog as either:
      - A plain string (shorthand for ``{file: <path>, mode: copy}``)
      - A mapping with ``file`` and ``mode`` keys
    """
    file: str
    mode: str = "copy"  # "copy" or "append"

    @classmethod
    def from_value(cls, value: object) -> Optional["TargetSpec"]:
        """Create a TargetSpec from a catalog target value.

        Returns ``None`` if the value is ``None`` (tool not supported).
        """
        if value is None:
            return None
        if isinstance(value, str):
            return cls(file=value, mode="copy")
        if isinstance(value, dict):
            file_val = value.get("file")
            if file_val is None:
                raise ValueError("Target mapping must include a 'file' key.")
            mode = value.get("mode", "copy")
            if mode not in ("copy", "append"):
                raise ValueError(f"Invalid target mode '{mode}'. Must be 'copy' or 'append'.")
            return cls(file=str(file_val), mode=mode)
        raise ValueError(f"Unexpected target value type: {type(value)}")


@dataclass
class CatalogItem:
    name: str
    type: str
    source: str
    description: str
    compatibility: list[str] = field(default_factory=list)
    targets: dict[str, Optional[TargetSpec]] = field(default_factory=dict)
    steering_inject: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> CatalogItem:
        raw_targets = data.get("targets", {})
        parsed_targets: dict[str, Optional[TargetSpec]] = {}
        for tool, value in raw_targets.items():
            parsed_targets[tool] = TargetSpec.from_value(value)
        return cls(
            name=data["name"],
            type=data["type"],
            source=data["source"],
            description=data.get("description", ""),
            compatibility=data.get("compatibility", []),
            targets=parsed_targets,
        )


def _read_skill_steering_inject(repo_root: Path, source: str) -> Optional[str]:
    """Read the steering-inject value from a skill's SKILL.md metadata."""
    skill_md = repo_root / source / SKILL_ENTRY
    if not skill_md.exists():
        return None

    text = skill_md.read_text()
    # Extract YAML front-matter between --- delimiters.
    fm_match = re.match(r"^---\s*\n(.+?)\n---", text, re.DOTALL)
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
        try:
            item = CatalogItem.from_dict(data)
        except (ValueError, KeyError) as exc:
            name = data.get("name", "<unknown>")
            print(
                f"Error: invalid catalog entry '{name}': {exc}",
                file=sys.stderr,
            )
            sys.exit(1)
        # For skills, read steering-inject from the SKILL.md metadata.
        if item.type == "skill":
            item.steering_inject = _read_skill_steering_inject(repo_root, item.source)

        # Validate: an item must not combine steering-inject with an
        # append-mode target that writes to the same steering root file.
        # Both mechanisms append marked blocks to AGENTS.md and their
        # marker namespaces could collide.
        if item.steering_inject:
            for tool_name, spec in item.targets.items():
                if spec and spec.mode == "append" and spec.file == STEERING_ROOT_DEFAULT:
                    print(
                        f"Error: catalog entry '{item.name}' has both "
                        f"steering-inject and an append-mode target to "
                        f"{STEERING_ROOT_DEFAULT} (tool '{tool_name}'). "
                        f"These two mechanisms would write overlapping "
                        f"marked blocks to the same file. Use one or the other.",
                        file=sys.stderr,
                    )
                    sys.exit(1)

        items.append(item)
    return items


# ---------------------------------------------------------------------------
# Install manifest (local registry of installed items)
# ---------------------------------------------------------------------------

def _manifest_path(repo_root: Path) -> Path:
    """Return the path to the local install manifest."""
    return repo_root / MANIFEST_FILE


def _is_valid_manifest_entry(entry: object) -> bool:
    """Return True if the manifest entry has the expected structure."""
    if not isinstance(entry, dict):
        return False
    required_keys = {"name", "dest", "tool"}
    if not required_keys.issubset(entry.keys()):
        return False
    if not all(isinstance(entry[key], str) for key in required_keys):
        return False
    if "target" in entry and not isinstance(entry["target"], str):
        return False
    return True


def _load_manifest(repo_root: Path) -> list[dict]:
    """Load the install manifest, returning an empty list if it doesn't exist."""
    path = _manifest_path(repo_root)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(
            f"Warning: ignoring unreadable or invalid manifest at {path}: {exc}",
            file=sys.stderr,
        )
        return []

    if not isinstance(raw, list):
        print(
            f"Warning: ignoring invalid manifest at {path}: expected a JSON list.",
            file=sys.stderr,
        )
        return []

    valid_entries = [entry for entry in raw if _is_valid_manifest_entry(entry)]
    if len(valid_entries) != len(raw):
        n_bad = len(raw) - len(valid_entries)
        print(
            f"Warning: ignoring {n_bad} invalid manifest "
            f"entr{'y' if n_bad == 1 else 'ies'} in {path}.",
            file=sys.stderr,
        )
    return valid_entries


def _save_manifest(repo_root: Path, entries: list[dict]) -> None:
    """Write the install manifest to disk atomically."""
    path = _manifest_path(repo_root)
    tmp_path = path.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(entries, indent=2) + "\n")
        tmp_path.replace(path)
    except OSError as exc:
        print(
            f"Warning: failed to write manifest at {path}: {exc}",
            file=sys.stderr,
        )
        # Clean up the temp file if it was written but rename failed.
        tmp_path.unlink(missing_ok=True)


def _add_manifest_entry(
    repo_root: Path,
    *,
    name: str,
    dest: Path,
    tool: str,
    target: str,
    mode: str = "copy",
) -> None:
    """Record an installation in the manifest, replacing any existing entry
    for the same (name, dest, tool) combination."""
    entries = _load_manifest(repo_root)
    # Remove any existing entry for this exact combo.
    entries = [
        e for e in entries
        if not (e["name"] == name and e["dest"] == str(dest) and e["tool"] == tool)
    ]
    entries.append({
        "name": name,
        "dest": str(dest),
        "tool": tool,
        "target": target,
        "mode": mode,
    })
    _save_manifest(repo_root, entries)


def _remove_manifest_entry(
    repo_root: Path,
    *,
    name: str,
    dest: Path,
    tool: str,
) -> None:
    """Remove an installation record from the manifest."""
    entries = _load_manifest(repo_root)
    entries = [
        e for e in entries
        if not (e["name"] == name and e["dest"] == str(dest) and e["tool"] == tool)
    ]
    _save_manifest(repo_root, entries)


# ---------------------------------------------------------------------------
# Steering injection
# ---------------------------------------------------------------------------

def _steering_root_file(tool: str) -> str:
    """Return the root steering file path for a given tool."""
    return STEERING_ROOT_DEFAULT


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
    pattern = rf"\n?{re.escape(marker_open)}\n.*?\n{re.escape(marker_close)}\n?"
    cleaned = re.sub(pattern, "", content, flags=re.DOTALL)
    cleaned = _normalize_trailing_blank_lines(cleaned)
    root_file.write_text(cleaned)

    print(f"  ↳ Removed steering from {root_file}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(
    catalog: list[CatalogItem],
    *,
    item_type: Optional[str] = None,
    tool: Optional[str] = None,
) -> None:
    """Print a filtered list of catalog items."""
    filtered = catalog
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
    dry_run: bool = False,
) -> None:
    """Install a single catalog item."""
    target_spec = item.targets.get(tool)
    if target_spec is None:
        print(f"Error: '{item.name}' is not compatible with {tool}.", file=sys.stderr)
        sys.exit(1)

    src = repo_root / item.source
    dst = dest / target_spec.file

    if not src.exists():
        print(f"Error: source file not found: {src}", file=sys.stderr)
        sys.exit(1)

    if target_spec.mode == "append":
        _install_append(item, src=src, dst=dst, dry_run=dry_run)
    else:
        written = _install_copy(item, src=src, dst=dst, dry_run=dry_run)
        if not written:
            return

    if not dry_run:
        # Inject steering text into the tool's root steering file if configured.
        # This is idempotent — skips if already present.
        inject_steering(dest, tool, item, dry_run=False)

        # Record in the local install manifest (including the resolved target path).
        # Always record so the manifest stays consistent even if the content was
        # already present (e.g. re-running install after manual manifest deletion).
        _add_manifest_entry(
            repo_root, name=item.name, dest=dest, tool=tool,
            target=str(dst), mode=target_spec.mode,
        )
    else:
        inject_steering(dest, tool, item, dry_run=True)


def _install_copy(
    item: CatalogItem,
    *,
    src: Path,
    dst: Path,
    dry_run: bool,
) -> bool:
    """Install by copying source to destination.

    Returns ``True`` if the content was (or would be) written, ``False`` if
    the user declined to overwrite an existing target.
    """
    if dry_run:
        print(f"[dry-run] Would copy:")
        print(f"  {src}")
        print(f"  → {dst}")
        if dst.exists() or dst.is_symlink():
            print(f"  ⚠ Destination already exists and would be overwritten.")
        return True

    if dst.exists() or dst.is_symlink():
        response = input(f"'{dst}' already exists. Overwrite? [y/N] ").strip().lower()
        if response != "y":
            print("Skipped.")
            return False
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

    print(f"✓ Installed '{item.name}' → {dst}")
    return True


def _append_marker_open(name: str) -> str:
    return f"<!-- {INJECT_PREFIX}:append:{name} -->"


def _append_marker_close(name: str) -> str:
    return f"<!-- /{INJECT_PREFIX}:append:{name} -->"


def _normalize_trailing_blank_lines(text: str) -> str:
    """Collapse runs of 3+ consecutive newlines down to 2 (one blank line)."""
    return re.sub(r"\n{3,}", "\n\n", text)


def _install_append(
    item: CatalogItem,
    *,
    src: Path,
    dst: Path,
    dry_run: bool,
) -> None:
    """Install by appending source content to destination file, wrapped in markers."""
    marker_open = _append_marker_open(item.name)
    marker_close = _append_marker_close(item.name)

    # Read source content.
    if src.is_dir():
        print(f"Error: cannot append a directory source to a file target.", file=sys.stderr)
        sys.exit(1)
    content = src.read_text()

    # Guard against target being a directory.
    if dst.exists() and dst.is_dir():
        print(f"Error: cannot append to directory target {dst}.", file=sys.stderr)
        sys.exit(1)

    # Don't double-append.
    if dst.exists() and marker_open in dst.read_text():
        if dry_run:
            print(f"[dry-run] '{item.name}' already appended to {dst}, would skip.")
        else:
            print(f"'{item.name}' already appended to {dst}, skipping.")
        return

    block = f"{marker_open}\n{content}\n{marker_close}\n"

    if dry_run:
        print(f"[dry-run] Would append '{item.name}' to {dst}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Prepend a blank-line separator when appending to a file that already
    # has content, so the marker block doesn't run into existing text.
    # Skip the separator for new or empty files to avoid a leading blank line.
    separator = "\n" if dst.exists() and dst.stat().st_size > 0 else ""

    with dst.open("a") as f:
        f.write(f"{separator}{block}")

    print(f"✓ Installed '{item.name}' → {dst} (appended)")


def cmd_uninstall(
    item: CatalogItem,
    *,
    repo_root: Path,
    dest: Path,
    tool: str,
    dry_run: bool = False,
) -> None:
    """Remove a previously installed catalog item."""
    target_spec = item.targets.get(tool)
    if target_spec is None:
        print(f"Error: '{item.name}' has no target for {tool}.", file=sys.stderr)
        sys.exit(1)

    dst = dest / target_spec.file

    # Determine the install mode. Prefer the mode stored in the manifest
    # (source of truth for how the item was originally installed). Fall
    # back to the current catalog spec for older manifest entries.
    entries = _load_manifest(repo_root)
    manifest_entry = next(
        (e for e in entries
         if e["name"] == item.name and e["dest"] == str(dest) and e["tool"] == tool),
        None,
    )
    mode = manifest_entry.get("mode", target_spec.mode) if manifest_entry else target_spec.mode

    # Prefer the resolved target path stored at install time. Fall back
    # to the current catalog target for manifests written before this
    # field was added.
    if manifest_entry and "target" in manifest_entry:
        stored = Path(manifest_entry["target"])
        dest_root = dest.resolve(strict=False)
        if stored.is_absolute():
            try:
                stored.relative_to(dest_root)
                dst = stored
            except ValueError:
                pass  # stored path outside dest — fall through to catalog default
        # else: non-absolute stored path — fall through to catalog default

    if mode == "append":
        _uninstall_append(item, repo_root=repo_root, dst=dst, dest=dest, tool=tool, dry_run=dry_run)
    else:
        _uninstall_copy(item, repo_root=repo_root, dst=dst, dest=dest, tool=tool, dry_run=dry_run)


def _uninstall_copy(
    item: CatalogItem,
    *,
    repo_root: Path,
    dst: Path,
    dest: Path,
    tool: str,
    dry_run: bool,
) -> None:
    """Uninstall a copy-mode item by removing the target file or directory."""
    # Treat broken symlinks as installed (exists() returns False for them).
    installed = dst.exists() or dst.is_symlink()

    if not installed:
        print(f"'{item.name}' is not installed at {dst}.")
        if not dry_run:
            _remove_manifest_entry(repo_root, name=item.name, dest=dest, tool=tool)
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

    # Remove from the local install manifest.
    _remove_manifest_entry(repo_root, name=item.name, dest=dest, tool=tool)


def _uninstall_append(
    item: CatalogItem,
    *,
    repo_root: Path,
    dst: Path,
    dest: Path,
    tool: str,
    dry_run: bool,
) -> None:
    """Uninstall an append-mode item by removing the marked block from the target file."""
    marker_open = _append_marker_open(item.name)

    if not dst.exists():
        print(f"'{item.name}' is not installed (file not found: {dst}).")
        if not dry_run:
            _remove_manifest_entry(repo_root, name=item.name, dest=dest, tool=tool)
        return

    if dst.is_dir():
        print(f"Cannot uninstall '{item.name}' from {dst}: target path is a directory, not a file.")
        if not dry_run:
            _remove_manifest_entry(repo_root, name=item.name, dest=dest, tool=tool)
        return

    try:
        content = dst.read_text()
    except OSError as exc:
        print(f"Cannot uninstall '{item.name}' from {dst}: failed to read target file ({exc}).")
        if not dry_run:
            _remove_manifest_entry(repo_root, name=item.name, dest=dest, tool=tool)
        return
    if marker_open not in content:
        print(f"'{item.name}' is not installed in {dst}.")
        if not dry_run:
            _remove_manifest_entry(repo_root, name=item.name, dest=dest, tool=tool)
        return

    if dry_run:
        print(f"[dry-run] Would remove '{item.name}' block from {dst}")
        remove_steering(dest, tool, item, dry_run=True)
        return

    marker_close = _append_marker_close(item.name)
    pattern = rf"\n?{re.escape(marker_open)}\n.*?\n{re.escape(marker_close)}\n?"
    cleaned = re.sub(pattern, "", content, flags=re.DOTALL)
    cleaned = _normalize_trailing_blank_lines(cleaned)
    dst.write_text(cleaned)

    print(f"✓ Uninstalled '{item.name}' (removed block from {dst})")

    # Remove injected steering text from the tool's root steering file.
    remove_steering(dest, tool, item, dry_run=False)

    # Remove from the local install manifest.
    _remove_manifest_entry(repo_root, name=item.name, dest=dest, tool=tool)


def _sync_copy(item: CatalogItem, *, src: Path, dst: Path) -> None:
    """Sync a copy-mode item by replacing the target."""
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

    print(f"✓ Synced '{item.name}' → {dst}")


def _sync_append(item: CatalogItem, *, src: Path, dst: Path) -> None:
    """Sync an append-mode item by removing the old block and re-appending."""
    marker_open = _append_marker_open(item.name)
    marker_close = _append_marker_close(item.name)

    if src.is_dir():
        print(
            f"Skipping '{item.name}': append mode requires a file source, "
            f"but got directory {src}",
        )
        return

    content = src.read_text()
    block = f"{marker_open}\n{content}\n{marker_close}\n"

    if dst.exists():
        if dst.is_dir():
            print(
                f"Skipping '{item.name}': append target is a directory, "
                f"not a file: {dst}",
            )
            return
        existing = dst.read_text()
        # Remove old block if present.
        if marker_open in existing:
            pattern = rf"\n?{re.escape(marker_open)}\n.*?\n{re.escape(marker_close)}\n?"
            existing = re.sub(pattern, "", existing, flags=re.DOTALL)
            existing = _normalize_trailing_blank_lines(existing)
            dst.write_text(existing)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)

    # Prepend a blank-line separator when appending to a file that already
    # has content, so the marker block doesn't run into existing text.
    separator = "\n" if dst.exists() and dst.stat().st_size > 0 else ""

    with dst.open("a") as f:
        f.write(f"{separator}{block}")

    print(f"✓ Synced '{item.name}' → {dst} (appended)")


def cmd_sync(
    catalog: list[CatalogItem],
    *,
    repo_root: Path,
    name: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """Re-copy installed items from the kit repo to their registered destinations.

    If *name* is given, only sync that item. Otherwise sync everything in the
    manifest.
    """
    entries = _load_manifest(repo_root)
    if not entries:
        print("Nothing to sync — the install manifest is empty.")
        print("Install items first with: python install.py install <name> --dest <path> --tool <tool>")
        return

    if name:
        entries = [e for e in entries if e["name"] == name]
        if not entries:
            print(f"No manifest entries found for '{name}'.")
            return

    catalog_map = {item.name: item for item in catalog}
    synced = 0
    would_sync = 0
    skipped = 0

    for entry in entries:
        item = catalog_map.get(entry["name"])
        if item is None:
            print(f"⚠ '{entry['name']}' is no longer in the catalog, skipping.")
            skipped += 1
            continue

        tool = entry["tool"]
        dest = Path(entry["dest"])

        dest_root = dest.resolve(strict=False)

        # Resolve the target spec from the current catalog.
        target_spec = item.targets.get(tool)
        if target_spec is None:
            print(f"⚠ '{item.name}' no longer has a target for {tool}, skipping.")
            skipped += 1
            continue

        # Prefer the resolved target path stored at install time. Fall back
        # to the current catalog target for manifests written before this
        # field was added.
        if "target" in entry:
            dst = Path(entry["target"])
            if not dst.is_absolute():
                print(f"⚠ Manifest target for '{item.name}' is not absolute: {dst}, skipping.")
                skipped += 1
                continue
            dst = dst.resolve(strict=False)
            try:
                dst.relative_to(dest_root)
            except ValueError:
                print(f"⚠ Manifest target for '{item.name}' is outside destination root: {dst}, skipping.")
                skipped += 1
                continue
        else:
            dst = dest_root / target_spec.file

        src = repo_root / item.source

        if not src.exists():
            print(f"⚠ Source missing for '{item.name}': {src}, skipping.")
            skipped += 1
            continue

        if not dest.is_dir():
            print(f"⚠ Destination directory missing: {dest}, skipping.")
            skipped += 1
            continue

        # Determine the install mode. Prefer the mode stored in the manifest
        # (source of truth for how the item was originally installed). Fall
        # back to the current catalog spec for older manifest entries.
        mode = entry.get("mode", target_spec.mode)

        if dry_run:
            if mode == "append":
                print(f"[dry-run] Would re-append '{item.name}' in {dst}")
            else:
                print(f"[dry-run] Would copy '{item.name}' → {dst}")
            would_sync += 1
            continue

        if mode == "append":
            _sync_append(item, src=src, dst=dst)
        else:
            _sync_copy(item, src=src, dst=dst)

        # Re-inject steering (idempotent — skips if already present).
        inject_steering(dest, tool, item, dry_run=False)
        synced += 1

    if dry_run:
        print(f"\nDone. {would_sync} would be synced, {skipped} skipped.")
    else:
        print(f"\nDone. {synced} synced, {skipped} skipped.")


# ---------------------------------------------------------------------------
# Argument resolution helpers
# ---------------------------------------------------------------------------

def prompt_choice(
    prompt_text: str,
    options: list[str],
    *,
    footer: Optional[str] = None,
    value_map: Optional[dict[str, str]] = None,
) -> str:
    """Present a numbered menu and return the user's choice.

    If *footer* is provided it is printed after the options.
    If *value_map* is provided, the display label is mapped back to the
    canonical value before returning.
    """
    print(prompt_text)
    for i, option in enumerate(options, 1):
        print(f"  {i}) {option}")
    if footer:
        print(f"\n{footer}")
    while True:
        try:
            raw = input("Enter choice: ").strip()
            idx = int(raw)
            if 1 <= idx <= len(options):
                chosen = options[idx - 1]
                if value_map and chosen in value_map:
                    return value_map[chosen]
                return chosen
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
    ls.add_argument("--type", dest="item_type", help="Filter by type (instruction, hook, skill)")
    ls.add_argument("--tool", help="Filter by compatible tool")

    # install
    inst = sub.add_parser("install", help="Install an extension")
    inst.add_argument("name", help="Item name from the catalog")
    inst.add_argument("--dest", required=True, help="Target project directory")
    inst.add_argument("--tool", help="Target tool (prompted if omitted)")
    inst.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    # uninstall
    uninst = sub.add_parser("uninstall", help="Remove an installed extension")
    uninst.add_argument("name", help="Item name from the catalog")
    uninst.add_argument("--dest", required=True, help="Target project directory")
    uninst.add_argument("--tool", help="Target tool (prompted if omitted)")
    uninst.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    # sync
    syn = sub.add_parser("sync", help="Re-copy all installed items from the kit repo to their targets")
    syn.add_argument("name", nargs="?", default=None, help="Sync only this item (optional, syncs all if omitted)")
    syn.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    catalog = load_catalog(repo_root)

    if args.command == "list":
        cmd_list(catalog, item_type=args.item_type, tool=args.tool)
        return

    if args.command == "sync":
        cmd_sync(catalog, repo_root=repo_root, name=args.name, dry_run=args.dry_run)
        return

    dest = Path(args.dest).resolve()
    if not dest.is_dir():
        print(f"Error: destination '{dest}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    item = find_item(catalog, args.name)
    tool = resolve_tool(args.tool, dest, item)

    if args.command == "install":
        cmd_install(item, repo_root=repo_root, dest=dest, tool=tool, dry_run=args.dry_run)
    elif args.command == "uninstall":
        cmd_uninstall(item, repo_root=repo_root, dest=dest, tool=tool, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
