"""CLI entry point for RepoDoctor."""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from repodoctor import __version__
from repodoctor.config import get_default_config
from repodoctor.output.html_report import write_html
from repodoctor.output.json_output import write_json
from repodoctor.output.terminal import format_terminal
from repodoctor.scanner import scan

app = typer.Typer(
    name="repodoctor",
    help="CLI tool that detects technical debt in codebases.",
    add_completion=False,
)
console = Console()


@app.command("scan")
def scan_command(
    path: Path = typer.Argument(
        Path("."),
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Directory to scan",
    ),
    format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format: terminal, json, html",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        path_type=Path,
        help="Output file path (for json/html)",
    ),
    threshold: str = typer.Option(
        "low",
        "--threshold",
        "-t",
        help="Minimum severity to display: low, medium, high, critical",
    ),
    exclude: list[str] = typer.Option(
        [],
        "--exclude",
        "-e",
        help="Glob patterns to exclude (in addition to defaults)",
    ),
    no_git: bool = typer.Option(
        False,
        "--no-git",
        help="Skip Git analysis",
    ),
) -> None:
    """Scan a codebase for technical debt."""
    config = get_default_config()
    if exclude:
        config = config  # Exclude patterns applied in get_exclude_patterns when we pass extra

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Scanning codebase...", total=None)
        result = scan(path, config=config, skip_git=no_git, extra_exclude=exclude or None)

    if format == "terminal":
        format_terminal(result, console)
    elif format == "json":
        out_path = output or path / "repodoctor-report.json"
        write_json(result, out_path)
        console.print(f"[green]JSON report written to {out_path}[/green]")
    elif format == "html":
        out_path = output or path / "repodoctor-report.html"
        write_html(result, out_path)
        console.print(f"[green]HTML report written to {out_path}[/green]")
    else:
        typer.echo(f"Unknown format '{format}'. Use terminal, json, or html.")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Print RepoDoctor version."""
    typer.echo(f"repodoctor {__version__}")


def main() -> None:
    """Entry point for the repodoctor CLI."""
    app()


if __name__ == "__main__":
    main()
