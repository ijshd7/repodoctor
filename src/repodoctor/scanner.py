"""Orchestrator that runs all analyzers and collects results."""

import fnmatch
from pathlib import Path

from repodoctor.analyzers.complexity import analyze_complexity
from repodoctor.analyzers.dependencies import analyze_dependencies
from repodoctor.analyzers.git_analyzer import analyze_git
from repodoctor.analyzers.duplication import analyze_duplication
from repodoctor.config import Config, get_default_config
from repodoctor.models import FileMetrics, ScanResult
from repodoctor.scoring import compute_debt_score
from repodoctor.parsers.treesitter import detect_language, parse_file


def _should_exclude(file_path: Path, root: Path, exclude_patterns: tuple[str, ...]) -> bool:
    """Check if file should be excluded based on glob patterns."""
    try:
        rel = file_path.relative_to(root)
    except ValueError:
        rel = file_path
    parts = rel.parts
    for pattern in exclude_patterns:
        # Check if any path component matches
        for i, part in enumerate(parts):
            if fnmatch.fnmatch(part, pattern):
                return True
            if fnmatch.fnmatch(str(Path(*parts[: i + 1])), pattern):
                return True
        if fnmatch.fnmatch(str(rel), pattern):
            return True
    return False


def _collect_source_files(root: Path, exclude_patterns: tuple[str, ...]) -> list[Path]:
    """Collect all parseable source files under root."""
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _should_exclude(path, root, exclude_patterns):
            continue
        if detect_language(path):
            files.append(path)
    return files


def scan(
    path: Path,
    config: Config | None = None,
    skip_git: bool = False,
    extra_exclude: list[str] | None = None,
) -> ScanResult:
    """
    Scan a directory for technical debt.

    Args:
        path: Root directory to scan
        config: Configuration (uses defaults if None)
        skip_git: If True, skip Git analysis

    Returns:
        ScanResult with all findings and metrics
    """
    cfg = config or get_default_config()
    result = ScanResult(root_path=path)
    exclude = cfg.get_exclude_patterns(extra=extra_exclude)

    # 1. Collect and parse source files
    source_files = _collect_source_files(path, exclude)
    for file_path in source_files:
        parsed = parse_file(file_path)
        if parsed:
            try:
                rel = str(file_path.relative_to(path))
            except ValueError:
                rel = str(file_path)
            result.file_metrics.append(
                FileMetrics(
                    path=rel,
                    line_count=parsed["line_count"],
                    functions=parsed["functions"],
                    imports=parsed["imports"],
                    language=parsed.get("language"),
                )
            )

    # 2. Run complexity analyzer
    analyze_complexity(path, result, cfg, result.file_metrics)

    # 3. Run duplication detector
    analyze_duplication(path, result, cfg, result.file_metrics)

    # 4. Run dependency analyzer
    analyze_dependencies(path, result, cfg, result.file_metrics)

    # 5. Run Git analyzer (graceful skip if not a repo)
    if not skip_git:
        analyze_git(path, result, cfg, result.file_metrics)

    # 6. Compute debt score
    compute_debt_score(result)

    return result
