"""
cli.py — Synaptic CLI built with Typer + Rich.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from synaptic import __version__

app = typer.Typer(
    name="synaptic",
    help="[bold cyan]synaptic[/] — visualize the dependency graph of any Python project.",
    rich_markup_mode="rich",
    add_completion=True,
)

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        rprint(f"[bold cyan]synaptic[/] version [bold]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


@app.command()
def scan(
    project: Path = typer.Argument(
        ...,
        help="Root path of the Python project to analyse.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    output: Path = typer.Option(
        Path("synaptic_graph.html"),
        "--output", "-o",
        help="Output file path. Extension determines format: .html (interactive) or .svg.",
    ),
    cloud: bool = typer.Option(True,  "--cloud/--no-cloud",  help="Detect AWS / GCP / Azure SDK usage."),
    http:  bool = typer.Option(True,  "--http/--no-http",    help="Detect HTTP client library usage."),
    tests: bool = typer.Option(False, "--tests/--no-tests",  help="Include test files in the scan."),
    filter_stdlib:    bool = typer.Option(True,  "--filter-stdlib/--no-filter-stdlib",       help="Exclude Python stdlib modules from the graph."),
    filter_external:  bool = typer.Option(False, "--filter-external/--no-filter-external",   help="Exclude third-party (non-project) modules from the graph."),
    circular: bool = typer.Option(False, "--circular", "-c", help="Highlight circular dependencies in red."),
) -> None:
    """Scan *PROJECT* and generate a dependency graph."""

    console.print(
        Panel.fit(
            f"[bold cyan]synaptic[/] [dim]v{__version__}[/]\n"
            f"[dim]Scanning:[/] [bold]{project}[/]",
            border_style="cyan",
        )
    )

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:

        # 1. Scan files
        task = progress.add_task("Scanning .py files...", total=None)
        from synaptic.scanner import scan as do_scan
        files = do_scan(project, include_tests=tests)
        progress.update(task, description=f"[green]Found {len(files)} Python files[/]", completed=True)

        if not files:
            console.print("[yellow]No Python files found. Is the path correct?[/]")
            raise typer.Exit(1)

        # 2. Parse imports
        task = progress.add_task("Parsing imports (AST)...", total=None)
        from synaptic.parser import parse_project
        edges = parse_project(files, project)
        progress.update(task, description=f"[green]Parsed {len(edges)} import edges[/]", completed=True)

        # 3. Cloud detection
        cloud_deps = []
        if cloud:
            task = progress.add_task("Detecting cloud SDKs...", total=None)
            from synaptic.cloud_detector import detect as detect_cloud
            cloud_deps = detect_cloud(edges)
            progress.update(task, description=f"[green]Found {len(cloud_deps)} cloud dependencies[/]", completed=True)

        # 4. HTTP detection
        http_deps = []
        if http:
            task = progress.add_task("Detecting HTTP clients...", total=None)
            from synaptic.http_detector import detect as detect_http
            http_deps = detect_http(edges)
            progress.update(task, description=f"[green]Found {len(http_deps)} HTTP dependencies[/]", completed=True)

        # 5. Build graph
        task = progress.add_task("Building graph...", total=None)
        from synaptic.utils import get_stdlib_modules, resolve_internal_modules, choose_output_format
        from synaptic.graph import build, render_html, render_svg

        internal_modules = resolve_internal_modules(files, project)
        stdlib_modules = get_stdlib_modules()

        G = build(
            edges=edges,
            cloud_deps=cloud_deps,
            http_deps=http_deps,
            internal_modules=internal_modules,
            stdlib_modules=stdlib_modules,
            filter_stdlib=filter_stdlib,
            filter_external=filter_external,
            highlight_circular=circular,
        )
        progress.update(task, description=f"[green]Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges[/]", completed=True)

        # 6. Render
        fmt = choose_output_format(output)
        task = progress.add_task(f"Rendering {fmt.upper()}...", total=None)
        if fmt == "html":
            render_html(G, output)
        else:
            render_svg(G, output)
        progress.update(task, description=f"[green]Saved to {output}[/]", completed=True)

    # Summary
    console.print()
    console.print(
        Panel(
            f"[bold green]Done![/]\n\n"
            f"  [dim]Files scanned:[/]     [bold]{len(files)}[/]\n"
            f"  [dim]Import edges:[/]      [bold]{len(edges)}[/]\n"
            f"  [dim]Cloud deps:[/]        [bold]{len(cloud_deps)}[/]\n"
            f"  [dim]HTTP deps:[/]         [bold]{len(http_deps)}[/]\n"
            f"  [dim]Graph nodes:[/]       [bold]{G.number_of_nodes()}[/]\n"
            f"  [dim]Graph edges:[/]       [bold]{G.number_of_edges()}[/]\n\n"
            f"  [dim]Output:[/] [bold cyan]{output.resolve()}[/]",
            title="[bold cyan]synaptic[/]",
            border_style="green",
        )
    )


@app.command()
def tui(
    project: Path = typer.Argument(
        ...,
        help="Root path of the Python project to analyse.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    cloud: bool = typer.Option(True,  "--cloud/--no-cloud",  help="Detect AWS / GCP / Azure SDK usage."),
    http:  bool = typer.Option(True,  "--http/--no-http",    help="Detect HTTP client library usage."),
    tests: bool = typer.Option(False, "--tests/--no-tests",  help="Include test files in the scan."),
    filter_stdlib:   bool = typer.Option(True,  "--filter-stdlib/--no-filter-stdlib",     help="Exclude stdlib modules from the graph."),
    filter_external: bool = typer.Option(False, "--filter-external/--no-filter-external", help="Exclude third-party modules."),
    circular: bool = typer.Option(True, "--circular/--no-circular", help="Highlight circular dependencies."),
) -> None:
    """Launch the interactive TUI graph explorer for *PROJECT*."""
    from synaptic.scanner import scan as do_scan
    from synaptic.parser import parse_project
    from synaptic.cloud_detector import detect as detect_cloud
    from synaptic.http_detector import detect as detect_http
    from synaptic.graph import build
    from synaptic.utils import get_stdlib_modules, resolve_internal_modules
    from synaptic.tui import launch

    with console.status("[cyan]Building graph…[/]"):
        files = do_scan(project, include_tests=tests)
        if not files:
            console.print("[yellow]No Python files found.[/]")
            raise typer.Exit(1)

        edges = parse_project(files, project)
        cloud_deps = detect_cloud(edges) if cloud else []
        http_deps = detect_http(edges) if http else []

        internal_modules = resolve_internal_modules(files, project)
        stdlib_modules = get_stdlib_modules()

        G = build(
            edges=edges,
            cloud_deps=cloud_deps,
            http_deps=http_deps,
            internal_modules=internal_modules,
            stdlib_modules=stdlib_modules,
            filter_stdlib=filter_stdlib,
            filter_external=filter_external,
            highlight_circular=circular,
        )

    launch(G, project)


if __name__ == "__main__":
    app()
