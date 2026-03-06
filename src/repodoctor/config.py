"""Configuration and default thresholds for RepoDoctor."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass
class Config:
    """RepoDoctor configuration with default thresholds."""

    # Complexity thresholds
    max_function_lines: int = 50
    max_cyclomatic_complexity: int = 10
    max_file_lines: int = 300
    max_nesting_depth: int = 4

    # Duplication
    min_duplicate_lines: int = 6
    min_file_lines_for_duplication: int = 10

    # Git analysis
    max_commits_for_churn: int = 500

    # Default exclude patterns
    default_exclude: tuple[str, ...] = (
        "node_modules",
        "venv",
        "__pycache__",
        ".git",
        "dist",
        "build",
        "*.pyc",
        ".venv",
    )

    def get_exclude_patterns(self, extra: Sequence[str] | None = None) -> tuple[str, ...]:
        """Return combined exclude patterns."""
        if extra:
            return (*self.default_exclude, *extra)
        return self.default_exclude


def get_default_config() -> Config:
    """Return default configuration."""
    return Config()
