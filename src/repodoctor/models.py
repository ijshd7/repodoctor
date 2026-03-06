"""Data models for RepoDoctor scan results."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    """Severity level for findings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingKind(str, Enum):
    """Type of technical debt finding."""

    LONG_FUNCTION = "long_function"
    HIGH_COMPLEXITY = "high_complexity"
    LARGE_FILE = "large_file"
    DEEP_NESTING = "deep_nesting"
    DUPLICATION = "duplication"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    RISKY_MODULE = "risky_module"
    HOTSPOT = "hotspot"


@dataclass
class Finding:
    """A single technical debt finding."""

    kind: FindingKind
    severity: Severity
    file_path: str | Path
    message: str
    line_start: int | None = None
    line_end: int | None = None
    metric_value: float | int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileMetrics:
    """Metrics for a single file."""

    path: str | Path
    line_count: int
    functions: list[dict[str, Any]] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    language: str | None = None


@dataclass
class DuplicatePair:
    """A pair of duplicate code blocks."""

    file_a: str | Path
    file_b: str | Path
    line_start_a: int
    line_end_a: int
    line_start_b: int
    line_end_b: int
    duplicate_lines: int
    similarity_pct: float


@dataclass
class CircularDependency:
    """A detected circular dependency cycle."""

    modules: list[str]
    path: str  # e.g. "A -> B -> C -> A"


@dataclass
class GitMetrics:
    """Git-related metrics for the repo."""

    churn_by_file: dict[str, int] = field(default_factory=dict)
    hotspots: list[str] = field(default_factory=list)
    contributor_count_by_file: dict[str, int] = field(default_factory=dict)


@dataclass
class ScanResult:
    """Complete result of a RepoDoctor scan."""

    root_path: Path
    findings: list[Finding] = field(default_factory=list)
    file_metrics: list[FileMetrics] = field(default_factory=list)
    duplicate_pairs: list[DuplicatePair] = field(default_factory=list)
    circular_dependencies: list[CircularDependency] = field(default_factory=list)
    git_metrics: GitMetrics | None = None
    debt_score: float | None = None
    sub_scores: dict[str, float] = field(default_factory=dict)
