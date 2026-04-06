"""
utils.py — Shared helpers for synaptic.
"""

import sys
from pathlib import Path


def get_stdlib_modules() -> set[str]:
    """Return the set of top-level standard library module names."""
    if sys.version_info >= (3, 10):
        import sys as _sys
        return set(_sys.stdlib_module_names)  # type: ignore[attr-defined]

    # Fallback for older Pythons: a curated list of common stdlib modules
    return {
        "abc", "ast", "asyncio", "builtins", "collections", "contextlib",
        "copy", "dataclasses", "datetime", "enum", "functools", "hashlib",
        "io", "itertools", "json", "logging", "math", "operator", "os",
        "pathlib", "pickle", "platform", "pprint", "queue", "random",
        "re", "shutil", "signal", "socket", "sqlite3", "string", "struct",
        "subprocess", "sys", "tempfile", "threading", "time", "traceback",
        "typing", "unittest", "urllib", "uuid", "warnings", "weakref",
        "xml", "xmlrpc", "zipfile", "zlib",
    }


def resolve_internal_modules(files: list[Path], root: Path) -> set[str]:
    """Build the set of dotted module names that belong to the project."""
    from synaptic.parser import file_to_module
    return {file_to_module(f, root) for f in files}


def choose_output_format(output: Path) -> str:
    """Infer desired output format from the file extension."""
    suffix = output.suffix.lower()
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix in {".svg"}:
        return "svg"
    return "html"  # default
