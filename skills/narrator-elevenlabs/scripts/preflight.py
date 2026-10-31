#!/usr/bin/env python3
"""Preflight check for the narrator-elevenlabs skill.

Verifies all required packages are importable, installing any missing ones
from requirements.txt. Then checks the things pip can't install: an audio
player (mpv or ffplay) on PATH and the ELEVENLABS_API_KEY environment
variable. Prints setup steps for anything missing.

Exits 0 when everything is ready, non-zero otherwise.
"""

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Mapping of package names (as listed in requirements.txt) to their
# importable module names, for cases where they differ.
PACKAGE_TO_MODULE = {
    "httpx": "httpx",
    "numpy": "numpy",
    "pyyaml": "yaml",
    "sounddevice": "sounddevice",
    "soundfile": "soundfile",
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


# Where the Windows mpv installer puts mpv without adding it to PATH.
WINDOWS_MPV_DIRS = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "MPV Player",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "mpv",
]


def check_python_packages() -> bool:
    """Install any missing packages from requirements.txt. Returns True when all import."""
    if not REQUIREMENTS_FILE.exists():
        print(f"ERROR: requirements.txt not found at {REQUIREMENTS_FILE}", file=sys.stderr)
        return False

    packages = parse_requirements(REQUIREMENTS_FILE)
    missing = check_imports(packages)
    if not missing:
        print("Python packages: OK")
        return True

    print(f"Missing packages: {', '.join(missing)}. Installing...")
    if not install_requirements():
        return False
    still_missing = check_imports(packages)
    if still_missing:
        print(f"ERROR: Still missing after install: {', '.join(still_missing)}", file=sys.stderr)
        return False
    print("Python packages: installed")
    return True


def _on_saved_windows_path(directory: Path) -> bool:
    """Whether directory is on the user or machine PATH saved in the registry (new shells' PATH)."""
    import winreg

    keys = [
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]
    wanted = os.path.normcase(str(directory)).rstrip("\\")
    for root, sub in keys:
        try:
            with winreg.OpenKey(root, sub) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
        except OSError:
            continue
        entries = (os.path.normcase(os.path.expandvars(e)).rstrip("\\") for e in value.split(";"))
        if wanted in entries:
            return True
    return False


def audio_player_problem() -> str | None:
    """Setup steps when neither mpv nor ffplay is on PATH, else None."""
    if shutil.which("mpv") or shutil.which("ffplay"):
        print("Audio player: OK")
        return None

    if sys.platform == "win32":
        installed = next((d for d in WINDOWS_MPV_DIRS if (d / "mpv.exe").exists()), None)
        if installed and _on_saved_windows_path(installed):
            return (
                f"mpv is installed in {installed} and on your saved PATH, but this shell started before "
                "PATH was changed. Restart the coding tool so new shells pick it up."
            )
        if installed:
            return (
                f"mpv is installed in {installed} but isn't on PATH. Add it for your user, then restart "
                "the coding tool so new shells see it:\n"
                f"    [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';{installed}', 'User')"
            )
        steps = (
            "    winget install --id shinchiro.mpv --exact\n"
            "  The installer doesn't add mpv to PATH; run this preflight again afterwards for the PATH step."
        )
    elif sys.platform == "darwin":
        steps = "    brew install mpv"
    else:
        steps = "    sudo apt install mpv    (or your distribution's mpv package)"
    return f"No audio player found. Speech is played through mpv (recommended) or ffplay. Install mpv:\n{steps}"


def api_key_problem() -> str | None:
    """Setup steps when ELEVENLABS_API_KEY isn't set, else None."""
    if os.environ.get("ELEVENLABS_API_KEY", "").strip():
        print("ElevenLabs API key: set")
        return None
    if sys.platform == "win32":
        how = "    [Environment]::SetEnvironmentVariable('ELEVENLABS_API_KEY', '<your key>', 'User')    (PowerShell)"
    else:
        how = "    export ELEVENLABS_API_KEY='<your key>'    (add to ~/.zshrc or ~/.bashrc)"
    return (
        "ELEVENLABS_API_KEY is not set. Create a key at https://elevenlabs.io/app/settings/api-keys "
        "(it needs Text to Speech access), then set it for your user:\n"
        f"{how}\n"
        "  Or, in Claude Code, add it to the \"env\" block of .claude/settings.local.json. "
        "Restart the coding tool afterwards so it picks up the variable."
    )


def main() -> int:
    if not check_python_packages():
        return 1

    problems = [p for p in (audio_player_problem(), api_key_problem()) if p]
    if not problems:
        print("Ready.")
        return 0

    # On stdout with the status lines, so the steps read in order after them.
    print("\nSetup needed before the narrator can speak:")
    for i, problem in enumerate(problems, 1):
        print(f"\n{i}. {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
