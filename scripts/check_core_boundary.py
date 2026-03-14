#!/usr/bin/env python3
"""CI boundary check: ensure core modules don't import business logic.

The "core" modules (agent/registry.py, agent/loop.py, agent/types.py,
llm/, models/, tools/) should NOT import from application-specific
modules (api/, storage/, prompts/, email/, config.py, crypto.py).

This keeps the core reusable as a standalone library.

Usage:
    python scripts/check_core_boundary.py
    # Exit code 0 = clean, 1 = violations found
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "gridbert"

# Core modules — should be dependency-free from business logic
CORE_MODULES = [
    SRC / "agent" / "registry.py",
    SRC / "agent" / "loop.py",
    SRC / "agent" / "types.py",
    SRC / "llm",
    SRC / "models",
    SRC / "tools" / "tariff_compare.py",
    SRC / "tools" / "gas_compare.py",
    SRC / "tools" / "smartmeter.py",
    SRC / "tools" / "smartmeter_providers",
    SRC / "tools" / "load_profile.py",
    SRC / "tools" / "spot_analysis.py",
    SRC / "tools" / "battery_sim.py",
    SRC / "tools" / "pv_sim.py",
    SRC / "tools" / "energy_monitor.py",
    SRC / "tools" / "beg_advisor.py",
    SRC / "tools" / "web_search.py",
    SRC / "tools" / "file_utils.py",
]

# Business modules that core should NOT import at module level
FORBIDDEN_IMPORTS = [
    r"from gridbert\.api\b",
    r"from gridbert\.storage\b",
    r"from gridbert\.prompts\b",
    r"from gridbert\.email\b",
    r"from gridbert\.crypto\b",
    r"import gridbert\.api\b",
    r"import gridbert\.storage\b",
    r"import gridbert\.prompts\b",
    r"import gridbert\.email\b",
    r"import gridbert\.crypto\b",
    r"from gridbert\.config\b",
    r"import gridbert\.config\b",
]

# Allowed exceptions: lazy imports inside functions (indented)
# We only flag module-level (non-indented) imports
INDENT_RE = re.compile(r"^\s+")


def collect_py_files(paths: list[Path]) -> list[Path]:
    """Collect all .py files from paths (files or directories)."""
    files: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.py"))
    return sorted(set(files))


def check_file(filepath: Path) -> list[str]:
    """Return list of violation messages for a single file."""
    violations: list[str] = []
    try:
        lines = filepath.read_text().splitlines()
    except OSError:
        return []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Only check actual import statements
        if not (stripped.startswith("from ") or stripped.startswith("import ")):
            continue

        # Skip indented imports (lazy/deferred imports inside functions)
        if INDENT_RE.match(line):
            continue

        for pattern in FORBIDDEN_IMPORTS:
            if re.search(pattern, stripped):
                rel = filepath.relative_to(PROJECT_ROOT)
                violations.append(f"  {rel}:{lineno}: {stripped}")

    return violations


def main() -> int:
    py_files = collect_py_files(CORE_MODULES)
    all_violations: list[str] = []

    for f in py_files:
        all_violations.extend(check_file(f))

    if all_violations:
        print("Core boundary violations found!")
        print("Core modules must not import business logic at module level.\n")
        for v in all_violations:
            print(v)
        print(f"\n{len(all_violations)} violation(s) found.")
        return 1

    print(f"Core boundary check passed ({len(py_files)} files scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
