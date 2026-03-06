"""Shared utilities for RepoDoctor."""

from pathlib import Path


def resolve_relative_path(file_path: Path | str, root: Path) -> str:
    """Return file_path as string relative to root, or full string if not under root."""
    p = Path(file_path) if isinstance(file_path, str) else file_path
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def try_relative_to(file_path: Path | str, root: Path) -> Path | None:
    """Return file_path as Path relative to root, or None if not under root."""
    p = Path(file_path) if isinstance(file_path, str) else file_path
    try:
        return p.relative_to(root)
    except ValueError:
        return None
