"""
parser.py — Parse Python files with AST and extract import relationships.
"""

import ast
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ImportEdge:
    source: str          # dotted module name of the importing file
    target: str          # dotted module name being imported
    names: list[str] = field(default_factory=list)   # specific names imported


def file_to_module(path: Path, root: Path) -> str:
    """Convert a file path to a dotted module name relative to *root*."""
    rel = path.relative_to(root)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else path.stem


def parse_file(path: Path, root: Path) -> list[ImportEdge]:
    """Return all ImportEdge entries found in *path*."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    module_name = file_to_module(path, root)
    edges: list[ImportEdge] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(ImportEdge(source=module_name, target=alias.name))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = [a.name for a in node.names]
                # Handle relative imports: level > 0 means relative to current package
                target = node.module
                if node.level and node.level > 0:
                    pkg_parts = module_name.split(".")[: -node.level]
                    target = ".".join(pkg_parts + [node.module]) if pkg_parts else node.module
                edges.append(ImportEdge(source=module_name, target=target, names=names))

    return edges


def parse_project(files: list[Path], root: Path) -> list[ImportEdge]:
    """Aggregate all import edges across the entire project."""
    all_edges: list[ImportEdge] = []
    for f in files:
        all_edges.extend(parse_file(f, root))
    return all_edges
