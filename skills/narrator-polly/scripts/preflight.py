#!/usr/bin/env python3
"""Preflight dependency check for narrator-polly skill.

Verifies all required packages are importable. If any are missing,
installs them from requirements.txt. Exits 0 on success, non-zero on failure.
"""

import importlib
import subprocess
import sys
from pathlib import Path

# Mapping of package names (as listed in requirements.txt) to their
# importable module names, for cases where they differ.
PACKAGE_TO_MODULE = {
    "pyyaml": "yaml",
    "sounddevice": "sounddevice",
    "soundfile": "soundfile",
    "boto3": "boto3",
    "numpy": "numpy",
}

SKILL_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_FILE = SKILL_ROOT / "requirements.txt"


def parse_requirements(path: Path) -> list[str]:
    """Extract package names from requirements.txt (ignoring version specifiers)."""
    packages = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip version specifiers: split on any of >= <= == != ~= < >
        for sep in (">=", "<=", "==", "!=", "~=", "<", ">"):
            line = line.split(sep)[0]
        packages.append(line.strip())
    return packages


def check_imports(packages: list[str]) -> list[str]:
    """Return list of packages whose modules cannot be imported."""
    missing = []
    for pkg in packages:
        module_name = PACKAGE_TO_MODULE.get(pkg.lower(), pkg)
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pkg)
    return missing


def install_requirements() -> bool:
    """Run pip install from requirements.txt. Returns True on success."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE), "--quiet"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"pip install failed:\n{result.stderr}", file=sys.stderr)
        return False
    return True


def main() -> int:
    if not REQUIREMENTS_FILE.exists():
        print(f"ERROR: requirements.txt not found at {REQUIREMENTS_FILE}", file=sys.stderr)
        return 1

    packages = parse_requirements(REQUIREMENTS_FILE)
    if not packages:
        print("No dependencies listed in requirements.txt.")
        return 0

    missing = check_imports(packages)

    if not missing:
        print("All dependencies satisfied.")
        return 0

    print(f"Missing packages: {', '.join(missing)}. Installing...")
    if install_requirements():
        # Verify after install
        still_missing = check_imports(packages)
        if still_missing:
            print(
                f"ERROR: Still missing after install: {', '.join(still_missing)}",
                file=sys.stderr,
            )
            return 1
        print("All dependencies installed successfully.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
