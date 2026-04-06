"""
graph.py — Build a dependency graph and render it as SVG or interactive HTML.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from synaptic.parser import ImportEdge
from synaptic.cloud_detector import CloudDependency
from synaptic.http_detector import HttpDependency

# Node kinds → visual properties
_COLORS = {
    "internal": "#4F8EF7",   # blue
    "stdlib":   "#A0A0A0",   # grey
    "external": "#F7A24F",   # orange
    "AWS":      "#FF9900",   # AWS orange
    "GCP":      "#4285F4",   # Google blue
    "Azure":    "#0089D6",   # Azure blue
    "http":     "#E84393",   # pink
}


def build(
    edges: list[ImportEdge],
    cloud_deps: list[CloudDependency],
    http_deps: list[HttpDependency],
    internal_modules: set[str],
    stdlib_modules: set[str],
    filter_stdlib: bool = True,
    filter_external: bool = False,
    highlight_circular: bool = False,
) -> nx.DiGraph:
    G = nx.DiGraph()

    def node_kind(name: str) -> str:
        if name in internal_modules:
            return "internal"
        if name in stdlib_modules:
            return "stdlib"
        return "external"

    # Internal import edges
    for edge in edges:
        src_kind = node_kind(edge.source)
        tgt_kind = node_kind(edge.target)

        if filter_stdlib and (src_kind == "stdlib" or tgt_kind == "stdlib"):
            continue
        if filter_external and tgt_kind == "external":
            continue

        for n, k in [(edge.source, src_kind), (edge.target, tgt_kind)]:
            if n not in G:
                G.add_node(n, kind=k, color=_COLORS.get(k, "#cccccc"), label=n.split(".")[-1])

        G.add_edge(edge.source, edge.target, kind="import")

    # Cloud dependency edges
    for dep in cloud_deps:
        node_id = f"[{dep.provider}] {dep.sdk}"
        if node_id not in G:
            G.add_node(node_id, kind=dep.provider, color=_COLORS.get(dep.provider, "#cccccc"), label=dep.sdk)
        if dep.source not in G:
            G.add_node(dep.source, kind="internal", color=_COLORS["internal"], label=dep.source.split(".")[-1])
        G.add_edge(dep.source, node_id, kind="cloud")

    # HTTP dependency edges
    for dep in http_deps:
        node_id = f"[HTTP] {dep.library}"
        if node_id not in G:
            G.add_node(node_id, kind="http", color=_COLORS["http"], label=dep.library)
        if dep.source not in G:
            G.add_node(dep.source, kind="internal", color=_COLORS["internal"], label=dep.source.split(".")[-1])
        G.add_edge(dep.source, node_id, kind="http")

    # Mark circular dependencies
    if highlight_circular:
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles:
            for i, node in enumerate(cycle):
                next_node = cycle[(i + 1) % len(cycle)]
                if G.has_edge(node, next_node):
                    G[node][next_node]["circular"] = True

    return G


def render_svg(G: nx.DiGraph, output: Path) -> Path:
    """Render graph to SVG using graphviz."""
    try:
        import graphviz as gv
    except ImportError:
        raise RuntimeError("graphviz package not installed. Run: pip install graphviz")

    dot = gv.Digraph(
        name="synaptic",
        graph_attr={"rankdir": "LR", "bgcolor": "#1a1a2e", "fontname": "Helvetica"},
        node_attr={"style": "filled", "fontname": "Helvetica", "fontcolor": "white", "fontsize": "11"},
        edge_attr={"color": "#666688", "arrowsize": "0.7"},
    )

    for node, data in G.nodes(data=True):
        color = data.get("color", "#cccccc")
        label = data.get("label", node)
        dot.node(node, label=label, fillcolor=color)

    for src, tgt, data in G.edges(data=True):
        attrs: dict[str, str] = {}
        if data.get("circular"):
            attrs = {"color": "#FF4444", "penwidth": "2"}
        elif data.get("kind") == "cloud":
            attrs = {"color": "#FF9900", "style": "dashed"}
        elif data.get("kind") == "http":
            attrs = {"color": "#E84393", "style": "dashed"}
        dot.edge(src, tgt, **attrs)

    out = output.with_suffix("")
    try:
        dot.render(str(out), format="svg", cleanup=True)
    except Exception as exc:
        if "ExecutableNotFound" in type(exc).__name__ or "dot" in str(exc).lower():
            raise RuntimeError(
                "Graphviz binary not found. Install it with:\n"
                "  sudo apt install graphviz   # Debian/Ubuntu/WSL\n"
                "  brew install graphviz       # macOS"
            ) from exc
        raise
    return output


def render_html(G: nx.DiGraph, output: Path) -> Path:
    """Render interactive HTML graph using pyvis."""
    try:
        from pyvis.network import Network
    except ImportError:
        raise RuntimeError("pyvis package not installed. Run: pip install pyvis")

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="white",
        directed=True,
        notebook=False,
    )
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150)

    for node, data in G.nodes(data=True):
        color = data.get("color", "#cccccc")
        label = data.get("label", node)
        title = f"<b>{node}</b><br/>kind: {data.get('kind', '?')}"
        net.add_node(node, label=label, color=color, title=title, size=20)

    for src, tgt, data in G.edges(data=True):
        color = "#FF4444" if data.get("circular") else (
            "#FF9900" if data.get("kind") == "cloud" else (
            "#E84393" if data.get("kind") == "http" else "#666688"
        ))
        net.add_edge(src, tgt, color=color, arrows="to")

    net.write_html(str(output))
    return output
