"""Complexity analyzer: long functions, high cyclomatic complexity, large files, deep nesting."""

from pathlib import Path

from repodoctor.config import Config
from repodoctor.utils import resolve_relative_path
from repodoctor.models import Finding, FindingKind, FileMetrics, ScanResult, Severity


def _severity_from_complexity(complexity: int, threshold: int) -> Severity:
    """Map complexity value to severity."""
    ratio = complexity / max(threshold, 1)
    if ratio >= 2.0:
        return Severity.CRITICAL
    if ratio >= 1.5:
        return Severity.HIGH
    if ratio >= 1.0:
        return Severity.MEDIUM
    return Severity.LOW


def _severity_from_lines(lines: int, threshold: int) -> Severity:
    """Map line count to severity."""
    ratio = lines / max(threshold, 1)
    if ratio >= 2.0:
        return Severity.CRITICAL
    if ratio >= 1.5:
        return Severity.HIGH
    if ratio >= 1.0:
        return Severity.MEDIUM
    return Severity.LOW


def analyze_complexity(
    path: Path,
    result: ScanResult,
    config: Config,
    file_metrics: list[FileMetrics],
) -> None:
    """
    Analyze complexity from file metrics and add findings.

    Called by scanner after file_metrics are populated.
    """
    for fm in file_metrics:
        file_path = Path(fm.path) if isinstance(fm.path, str) else fm.path
        rel_path = resolve_relative_path(file_path, path)

        # Large file
        if fm.line_count > config.max_file_lines:
            result.findings.append(
                Finding(
                    kind=FindingKind.LARGE_FILE,
                    severity=_severity_from_lines(fm.line_count, config.max_file_lines),
                    file_path=rel_path,
                    message=f"File has {fm.line_count} lines (threshold: {config.max_file_lines})",
                    metric_value=fm.line_count,
                )
            )

        for func in fm.functions:
            # Long function
            line_count = func.get("line_count", func["line_end"] - func["line_start"] + 1)
            if line_count > config.max_function_lines:
                result.findings.append(
                    Finding(
                        kind=FindingKind.LONG_FUNCTION,
                        severity=_severity_from_lines(line_count, config.max_function_lines),
                        file_path=rel_path,
                        message=f"Function '{func['name']}' has {line_count} lines (threshold: {config.max_function_lines})",
                        line_start=func["line_start"],
                        line_end=func["line_end"],
                        metric_value=line_count,
                    )
                )

            # High cyclomatic complexity
            complexity = func.get("complexity", 1)
            if complexity > config.max_cyclomatic_complexity:
                result.findings.append(
                    Finding(
                        kind=FindingKind.HIGH_COMPLEXITY,
                        severity=_severity_from_complexity(complexity, config.max_cyclomatic_complexity),
                        file_path=rel_path,
                        message=f"Function '{func['name']}' has cyclomatic complexity {complexity} (threshold: {config.max_cyclomatic_complexity})",
                        line_start=func["line_start"],
                        line_end=func["line_end"],
                        metric_value=complexity,
                    )
                )

            # Deep nesting
            nesting = func.get("nesting_depth", 0)
            if nesting > config.max_nesting_depth:
                result.findings.append(
                    Finding(
                        kind=FindingKind.DEEP_NESTING,
                        severity=_severity_from_lines(nesting, config.max_nesting_depth),
                        file_path=rel_path,
                        message=f"Function '{func['name']}' has nesting depth {nesting} (threshold: {config.max_nesting_depth})",
                        line_start=func["line_start"],
                        line_end=func["line_end"],
                        metric_value=nesting,
                    )
                )
