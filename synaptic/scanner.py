"""
scanner.py — Recursively walk a project directory and collect .py files.
"""

from pathlib import Path

IGNORE_DIRS = {
    "venv", ".venv", "env", ".env",
    "__pycache__", ".git", ".tox",
    "node_modules", "dist", "build", ".mypy_cache",
    ".pytest_cache", "site-packages",
}


def scan(
    root: Path,
    include_tests: bool = False,
) -> list[Path]:
    """Return all .py files under *root*, skipping ignored directories."""
    result: list[Path] = []

    for path in sorted(root.rglob("*.py")):
        parts = set(path.parts)
        if parts & IGNORE_DIRS:
            continue
        if not include_tests and _is_test(path):
            continue
        result.append(path)

    return result


def _is_test(path: Path) -> bool:
    """Heuristic: skip files/dirs that look like tests."""
    lowered = [p.lower() for p in path.parts]
    return any(
        p in {"tests", "test", "testing"} or p.startswith("test_")
        for p in lowered
    ) or path.stem.startswith("test_") or path.stem.endswith("_test")
