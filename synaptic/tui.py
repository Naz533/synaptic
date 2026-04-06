"""
tui.py — Interactive TUI for synaptic using Textual.

Layout:
  ┌─────────────────────────────────────────────────────────┐
  │  synaptic — dependency graph                  v0.1.0    │
  ├──────────────┬──────────────────────────────────────────┤
  │              │                                          │
  │  Node List   │           Graph Canvas                   │
  │  (sidebar)   │      (Unicode art, navigable)            │
  │              │                                          │
  ├──────────────┴──────────────────────────────────────────┤
  │  Detail panel — selected node info                      │
  ├─────────────────────────────────────────────────────────┤
  │  [q] quit  [tab/↑↓] navigate  [f] filter  [r] reset    │
  └─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import networkx as nx
from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

# ─── Color palette ──────────────────────────────────────────────────────────

NODE_COLORS: dict[str, str] = {
    "internal": "#4F8EF7",
    "external": "#A0A0A0",
    "stdlib": "#555577",
    "AWS": "#FF9900",
    "GCP": "#4285F4",
    "Azure": "#0089D6",
    "http": "#E84393",
}

KIND_ICON: dict[str, str] = {
    "internal": "◉",
    "external": "○",
    "stdlib": "·",
    "AWS": "◈",
    "GCP": "◈",
    "Azure": "◈",
    "http": "◈",
}

EDGE_STYLES: dict[str, tuple[str, str]] = {
    "import": ("·", "#2a2a55"),
    "cloud": ("·", "#7a4400"),
    "http": ("·", "#6a1040"),
    "circular": ("·", "#aa1111"),
}


# ─── Graph Canvas ────────────────────────────────────────────────────────────


class GraphCanvas(Widget, can_focus=True):
    """Renders the dependency graph as a Unicode canvas."""

    COMPONENT_CLASSES = {"graph-canvas--selected"}

    DEFAULT_CSS = """
    GraphCanvas {
        background: #09091a;
        border: solid #1e1e3a;
        height: 1fr;
        padding: 0;
    }
    GraphCanvas:focus {
        border: solid #4F8EF7;
    }
    """

    selected_node: reactive[str | None] = reactive(None, layout=True)

    def __init__(self, graph: nx.DiGraph, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph = graph
        self._raw_layout: dict[str, tuple[float, float]] = {}
        self._compute_layout()
        # ordered list for keyboard navigation
        self._node_order: list[str] = list(graph.nodes())

    def _compute_layout(self) -> None:
        if not self.graph.nodes:
            return
        raw: dict[str, Any] = nx.spring_layout(
            self.graph, k=2.5, iterations=80, seed=42
        )
        self._raw_layout = {n: (float(x), float(y)) for n, (x, y) in raw.items()}

    def _to_screen(self, node: str, w: int, h: int) -> tuple[int, int]:
        x, y = self._raw_layout.get(node, (0.0, 0.0))
        margin_x, margin_y = 3, 2
        col = int((x + 1) / 2 * (w - margin_x * 2)) + margin_x
        row = int((y + 1) / 2 * (h - margin_y * 2)) + margin_y
        return col, row

    def _bresenham(
        self, x0: int, y0: int, x1: int, y1: int
    ) -> list[tuple[int, int]]:
        """Return integer (col, row) points along the line from (x0,y0) to (x1,y1)."""
        points: list[tuple[int, int]] = []
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x1 >= x0 else -1
        sy = 1 if y1 >= y0 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            points.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return points

    def render(self) -> Text:
        w, h = self.size
        if w < 10 or h < 4:
            return Text("resize terminal")

        # 2-D character grid: (char, style_str)
        grid: list[list[tuple[str, str]]] = [
            [(" ", "") for _ in range(w)] for _ in range(h)
        ]

        def set_cell(col: int, row: int, ch: str, style: str) -> None:
            if 0 <= row < h and 0 <= col < w:
                # Never overwrite a node cell with an edge cell
                existing_ch, _ = grid[row][col]
                if existing_ch == " " or not style:
                    grid[row][col] = (ch, style)

        def force_cell(col: int, row: int, ch: str, style: str) -> None:
            if 0 <= row < h and 0 <= col < w:
                grid[row][col] = (ch, style)

        # ── Pre-compute selected node's neighbours ──────────────────────────
        selected_neighbours: set[str] = set()
        if self.selected_node:
            selected_neighbours = set(self.graph.successors(self.selected_node)) | set(
                self.graph.predecessors(self.selected_node)
            )

        # ── Draw edges ──────────────────────────────────────────────────────
        for src, tgt, data in self.graph.edges(data=True):
            if src not in self._raw_layout or tgt not in self._raw_layout:
                continue
            x0, y0 = self._to_screen(src, w, h)
            x1, y1 = self._to_screen(tgt, w, h)

            kind = data.get("kind", "import")
            is_circular = data.get("circular", False)
            key = "circular" if is_circular else kind

            ch, base_style = EDGE_STYLES.get(key, EDGE_STYLES["import"])

            # Highlight edge when connecting to/from selected node
            highlighted = self.selected_node and (
                src == self.selected_node or tgt == self.selected_node
            )
            if highlighted:
                if is_circular:
                    style = "bold #FF4444"
                elif kind == "cloud":
                    style = "#FF9900"
                elif kind == "http":
                    style = "#E84393"
                else:
                    style = "#4F8EF7 dim"
            else:
                style = base_style

            # Sample the line — skip endpoints (they belong to nodes)
            points = self._bresenham(x0, y0, x1, y1)
            for col, row in points[2:-2]:
                set_cell(col, row, ch, style)

        # ── Draw nodes ──────────────────────────────────────────────────────
        for node, data in self.graph.nodes(data=True):
            if node not in self._raw_layout:
                continue
            col, row = self._to_screen(node, w, h)
            kind = data.get("kind", "internal")
            color = NODE_COLORS.get(kind, "#cccccc")
            label = data.get("label", node.split(".")[-1])
            icon = KIND_ICON.get(kind, "◉")

            is_selected = node == self.selected_node
            is_neighbour = node in selected_neighbours

            # Clip label to avoid overflowing
            max_label = 12
            label = label[:max_label]
            full = f"{icon} {label} "
            half = len(full) // 2

            if is_selected:
                bg = "on #0f2050"
                node_style = f"bold {color} {bg} underline"
                # Draw selection box around the node
                box_w = len(full) + 2
                force_cell(col - half - 1, row - 1, "┌" + "─" * box_w + "┐", "#4F8EF7")
                for c in range(col - half - 1, col - half + box_w + 1):
                    force_cell(c, row - 1, "─", "#4F8EF7")
                force_cell(col - half - 1, row - 1, "┌", "#4F8EF7")
                force_cell(col - half + box_w, row - 1, "┐", "#4F8EF7")
                force_cell(col - half - 1, row, "│", "#4F8EF7")
                force_cell(col - half + box_w, row, "│", "#4F8EF7")
                force_cell(col - half - 1, row + 1, "└", "#4F8EF7")
                force_cell(col - half + box_w, row + 1, "┘", "#4F8EF7")
                for c in range(col - half - 1, col - half + box_w + 1):
                    force_cell(c, row + 1, "─", "#4F8EF7")
                force_cell(col - half - 1, row + 1, "└", "#4F8EF7")
                force_cell(col - half + box_w, row + 1, "┘", "#4F8EF7")
            elif is_neighbour:
                bg = "on #1a1a3a"
                node_style = f"{color} {bg}"
            else:
                bg = "on #0d0d1f"
                node_style = f"dim {color} {bg}"

            for i, ch in enumerate(full):
                force_cell(col - half + i, row, ch, node_style)

        # ── Assemble Rich Text ───────────────────────────────────────────────
        text = Text(no_wrap=True, overflow="crop")
        for row_idx, row_data in enumerate(grid):
            for ch, style in row_data:
                if style:
                    text.append(ch, style=Style.parse(style) if style else Style.null())
                else:
                    text.append(ch)
            if row_idx < h - 1:
                text.append("\n")

        return text

    # ── Keyboard navigation ──────────────────────────────────────────────────

    def on_key(self, event: events.Key) -> None:
        if not self._node_order:
            return

        if self.selected_node is None:
            self.selected_node = self._node_order[0]
            self.post_message(NodeSelected(self.selected_node, self.graph))
            return

        idx = (
            self._node_order.index(self.selected_node)
            if self.selected_node in self._node_order
            else 0
        )

        if event.key in ("right", "down", "tab", "j", "l", "n"):
            new = self._node_order[(idx + 1) % len(self._node_order)]
        elif event.key in ("left", "up", "shift+tab", "k", "h", "p"):
            new = self._node_order[(idx - 1) % len(self._node_order)]
        else:
            return

        event.stop()
        self.selected_node = new
        self.post_message(NodeSelected(new, self.graph))

    def on_click(self, event: events.Click) -> None:
        """Select the node nearest to where the user clicked."""
        w, h = self.size
        best_node: str | None = None
        best_dist = float("inf")

        for node in self._raw_layout:
            col, row = self._to_screen(node, w, h)
            dist = math.hypot(event.x - col, event.y - row)
            if dist < best_dist:
                best_dist = dist
                best_node = node

        if best_node and best_dist < 8:
            self.selected_node = best_node
            self.post_message(NodeSelected(best_node, self.graph))
            self.focus()


# ─── Custom messages ─────────────────────────────────────────────────────────


class NodeSelected(Message):
    def __init__(self, node: str, graph: nx.DiGraph) -> None:
        super().__init__()
        self.node = node
        self.graph = graph


# ─── Sidebar node list ───────────────────────────────────────────────────────


class NodeList(Widget):
    DEFAULT_CSS = """
    NodeList {
        width: 26;
        border: solid #1e1e3a;
        background: #09091a;
    }
    NodeList .node-item {
        padding: 0 1;
        height: 1;
    }
    NodeList .node-item:hover {
        background: #1a1a3a;
    }
    NodeList Label {
        padding: 0 1;
        color: #666688;
    }
    """

    def __init__(self, graph: nx.DiGraph, canvas: GraphCanvas, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph = graph
        self.canvas = canvas

    def compose(self) -> ComposeResult:
        yield Label(f" {self.graph.number_of_nodes()} nodes  {self.graph.number_of_edges()} edges")
        yield Label("─" * 24)
        for node, data in sorted(self.graph.nodes(data=True), key=lambda x: x[0]):
            kind = data.get("kind", "internal")
            color = NODE_COLORS.get(kind, "#cccccc")
            icon = KIND_ICON.get(kind, "◉")
            label = data.get("label", node.split(".")[-1])
            item = Static(
                Text.assemble(
                    (f"{icon} ", f"bold {color}"),
                    (label[:18], f"{color}"),
                ),
                classes="node-item",
            )
            item.tooltip = node
            item._node_id = node  # type: ignore[attr-defined]
            yield item

    def on_click(self, event: events.Click) -> None:
        # Find which item was clicked
        for child in self.query(".node-item"):
            node_id = getattr(child, "_node_id", None)
            if node_id and child.region.contains(event.screen_x, event.screen_y):
                self.canvas.selected_node = node_id
                self.canvas.post_message(NodeSelected(node_id, self.graph))
                self.canvas.focus()
                break


# ─── Detail panel ────────────────────────────────────────────────────────────


class DetailPanel(Widget):
    DEFAULT_CSS = """
    DetailPanel {
        height: 6;
        border: solid #1e1e3a;
        background: #0a0a1a;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Select a node with [bold cyan]Tab[/] or click to inspect it.", id="detail-content")

    def show(self, node: str, graph: nx.DiGraph) -> None:
        data = graph.nodes.get(node, {})
        kind = data.get("kind", "internal")
        color = NODE_COLORS.get(kind, "#cccccc")
        icon = KIND_ICON.get(kind, "◉")

        successors = list(graph.successors(node))
        predecessors = list(graph.predecessors(node))

        # Check for circular deps
        circular_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("circular") and (u == node or v == node)
        ]

        lines = Text()
        lines.append(f"{icon} {node}\n", style=f"bold {color}")
        lines.append(f"  kind: ", style="dim")
        lines.append(f"{kind}\n", style=color)
        lines.append(f"  imports ({len(successors)}): ", style="dim")
        lines.append(", ".join(s.split(".")[-1] for s in successors[:6]) or "—", style="#4F8EF7")
        if len(successors) > 6:
            lines.append(f" +{len(successors)-6} more", style="dim")
        lines.append("\n")
        lines.append(f"  imported by ({len(predecessors)}): ", style="dim")
        lines.append(", ".join(p.split(".")[-1] for p in predecessors[:6]) or "—", style="#a0a0cc")
        if circular_edges:
            lines.append("\n  ⚠ circular dep detected", style="bold red")

        self.query_one("#detail-content", Static).update(lines)


# ─── Main App ────────────────────────────────────────────────────────────────


class SynapticApp(App[None]):
    """Interactive TUI for synaptic dependency graphs."""

    CSS = """
    Screen {
        background: #0d0d1a;
        layout: grid;
        grid-size: 2 3;
        grid-columns: 26 1fr;
        grid-rows: auto 1fr auto;
    }
    #header-row {
        column-span: 2;
        height: 1;
        background: #111122;
        color: #4F8EF7;
        text-align: center;
        padding: 0 2;
    }
    #node-list {
        row-span: 1;
        overflow-y: scroll;
    }
    #canvas {
        row-span: 1;
    }
    #detail {
        column-span: 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "next_node", "Next node", show=False),
        Binding("shift+tab", "prev_node", "Prev node", show=False),
        Binding("r", "reset_selection", "Reset"),
        Binding("f", "focus_canvas", "Focus graph"),
    ]

    def __init__(self, graph: nx.DiGraph, project: Path, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph = graph
        self.project = project

    def compose(self) -> ComposeResult:
        from synaptic import __version__

        n_nodes = self.graph.number_of_nodes()
        n_edges = self.graph.number_of_edges()

        canvas = GraphCanvas(self.graph, id="canvas")
        detail = DetailPanel(id="detail")

        yield Static(
            Text.assemble(
                ("⬡ synaptic", "bold #4F8EF7"),
                (f"  {self.project.name}", "#666688"),
                (f"  ·  {n_nodes} nodes  {n_edges} edges", "dim #444466"),
                (f"  ·  v{__version__}", "dim #333355"),
            ),
            id="header-row",
        )
        yield NodeList(self.graph, canvas, id="node-list")
        yield canvas
        yield detail
        yield Footer()

    def on_node_selected(self, message: NodeSelected) -> None:
        self.query_one("#detail", DetailPanel).show(message.node, message.graph)

    def action_next_node(self) -> None:
        self.query_one("#canvas", GraphCanvas).on_key(
            events.Key(self, "tab", character=None)
        )

    def action_prev_node(self) -> None:
        self.query_one("#canvas", GraphCanvas).on_key(
            events.Key(self, "shift+tab", character=None)
        )

    def action_reset_selection(self) -> None:
        canvas = self.query_one("#canvas", GraphCanvas)
        canvas.selected_node = None
        self.query_one("#detail", DetailPanel).query_one(
            "#detail-content", Static
        ).update("Select a node with [bold cyan]Tab[/] or click to inspect it.")

    def action_focus_canvas(self) -> None:
        self.query_one("#canvas", GraphCanvas).focus()


# ─── Entry point ─────────────────────────────────────────────────────────────


def launch(graph: nx.DiGraph, project: Path) -> None:
    """Start the TUI application."""
    SynapticApp(graph=graph, project=project).run()
