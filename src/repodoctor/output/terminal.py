"""Rich terminal output for RepoDoctor scan results."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from repodoctor.models import Finding, FindingKind, ScanResult, Severity
from repodoctor.scoring import get_severity_label


def _severity_style(severity: Severity) -> str:
    """Return Rich style for severity."""
    return {
        Severity.LOW: "dim",
        Severity.MEDIUM: "yellow",
        Severity.HIGH: "orange1",
        Severity.CRITICAL: "bold red",
    }.get(severity, "")


def _group_findings_by_kind(findings: list[Finding]) -> dict[FindingKind, list[Finding]]:
    """Group findings by kind."""
    groups: dict[FindingKind, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.kind, []).append(f)
    return groups


def _kind_label(kind: FindingKind) -> str:
    """Human-readable label for finding kind."""
    return {
        FindingKind.LONG_FUNCTION: "Long Functions",
        FindingKind.HIGH_COMPLEXITY: "High Complexity",
        FindingKind.LARGE_FILE: "Large Files",
        FindingKind.DEEP_NESTING: "Deep Nesting",
        FindingKind.DUPLICATION: "Duplication",
        FindingKind.CIRCULAR_DEPENDENCY: "Circular Dependencies",
        FindingKind.RISKY_MODULE: "Risky Modules",
        FindingKind.HOTSPOT: "Hotspots",
    }.get(kind, kind.value.replace("_", " ").title())


def _render_summary_panel(result: ScanResult, console: Console) -> None:
    """Render the summary panel with debt score."""
    finding_count = len(result.findings)
    file_count = len(result.file_metrics)
    score = result.debt_score or 0
    label = get_severity_label(score)
    score_style = "green" if score <= 25 else "yellow" if score <= 50 else "orange1" if score <= 75 else "red"
    sub_scores_text = ""
    if result.sub_scores:
        sub_scores_text = "\n".join(
            f"  {k}: [dim]{v:.1f}[/]" for k, v in result.sub_scores.items()
        )
    console.print()
    console.print(
        Panel(
            f"[bold]RepoDoctor Scan[/bold]\n\n"
            f"Technical Debt Score: [{score_style}]{score}/100[/] ({label})\n\n"
            f"Sub-scores:\n{sub_scores_text}\n\n"
            f"Scanned [cyan]{file_count}[/cyan] files\n"
            f"Found [cyan]{finding_count}[/cyan] findings",
            title="Summary",
            border_style="blue",
        )
    )


def _render_circular_deps(result: ScanResult, console: Console) -> None:
    """Render circular dependencies table."""
    if not result.circular_dependencies:
        return
    circ_table = Table(title="Circular Dependencies", show_header=True, header_style="bold")
    circ_table.add_column("Cycle", style="red")
    for cd in result.circular_dependencies[:10]:
        circ_table.add_row(cd.path)
    if len(result.circular_dependencies) > 10:
        circ_table.caption = f"Showing 10 of {len(result.circular_dependencies)}"
    console.print(circ_table)
    console.print()


def _render_duplicates(result: ScanResult, console: Console) -> None:
    """Render duplication table."""
    if not result.duplicate_pairs:
        return
    dup_table = Table(title="Duplication", show_header=True, header_style="bold")
    dup_table.add_column("File A", style="cyan")
    dup_table.add_column("Lines", style="dim")
    dup_table.add_column("File B", style="cyan")
    dup_table.add_column("Lines", style="dim")
    dup_table.add_column("Duplicate Lines", style="yellow")
    for dp in result.duplicate_pairs[:15]:
        dup_table.add_row(
            str(dp.file_a),
            f"L{dp.line_start_a}-{dp.line_end_a}",
            str(dp.file_b),
            f"L{dp.line_start_b}-{dp.line_end_b}",
            str(dp.duplicate_lines),
        )
    if len(result.duplicate_pairs) > 15:
        dup_table.caption = f"Showing 15 of {len(result.duplicate_pairs)}"
    console.print(dup_table)
    console.print()


def _render_hotspots(result: ScanResult, console: Console) -> None:
    """Render Git hotspots table."""
    if not result.git_metrics or not result.git_metrics.hotspots:
        return
    hot_table = Table(title="Git Hotspots", show_header=True, header_style="bold")
    hot_table.add_column("File", style="cyan")
    hot_table.add_column("Churn", style="yellow")
    for f in result.git_metrics.hotspots[:10]:
        churn = result.git_metrics.churn_by_file.get(f, 0)
        hot_table.add_row(f, str(churn))
    console.print(hot_table)
    console.print()


def format_terminal(result: ScanResult, console: Console | None = None) -> None:
    """
    Print scan results to the terminal using Rich.

    Args:
        result: ScanResult from scanner
        console: Rich Console (uses default if None)
    """
    console = console or Console()
    _render_summary_panel(result, console)
    _render_circular_deps(result, console)
    _render_duplicates(result, console)
    _render_hotspots(result, console)

    if not result.findings and not result.duplicate_pairs:
        console.print("[green]No technical debt findings.[/green]")
        return

    # Group and display findings by kind
    groups = _group_findings_by_kind(result.findings)
    for kind in [
        FindingKind.LONG_FUNCTION,
        FindingKind.HIGH_COMPLEXITY,
        FindingKind.LARGE_FILE,
        FindingKind.DEEP_NESTING,
        FindingKind.DUPLICATION,
        FindingKind.CIRCULAR_DEPENDENCY,
        FindingKind.RISKY_MODULE,
        FindingKind.HOTSPOT,
    ]:
        items = groups.get(kind, [])
        if not items:
            continue

        table = Table(title=_kind_label(kind), show_header=True, header_style="bold")
        table.add_column("File", style="cyan")
        table.add_column("Location", style="dim")
        table.add_column("Message", style="white")
        table.add_column("Severity", style="bold")

        for f in items[:20]:  # Top 20 per category
            loc = ""
            if f.line_start:
                loc = f"L{f.line_start}" + (f"–{f.line_end}" if f.line_end and f.line_end != f.line_start else "")
            table.add_row(
                str(f.file_path),
                loc,
                f.message[:80] + "…" if len(f.message) > 80 else f.message,
                f"[{_severity_style(f.severity)}]{f.severity.value}[/]",
            )

        if len(items) > 20:
            table.caption = f"Showing 20 of {len(items)}"
        console.print(table)
        console.print()
