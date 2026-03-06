"""Duplication detector using rolling hash (Rabin-Karp) for duplicate block detection."""

from pathlib import Path

from repodoctor.config import Config
from repodoctor.models import DuplicatePair, Finding, FindingKind, FileMetrics, ScanResult, Severity


def _normalize_line(line: str) -> str:
    """Normalize a line for comparison: strip, collapse whitespace."""
    return " ".join(line.split())


def _tokenize_lines(lines: list[str]) -> list[str]:
    """Tokenize lines for hashing (normalized, no empty lines in sequence)."""
    tokens = []
    for line in lines:
        norm = _normalize_line(line)
        if norm or (tokens and tokens[-1]):  # Keep non-empty or break empty runs
            tokens.append(norm)
    return tokens


def _rolling_hash(tokens: list[str], base: int = 31, mod: int = 10**9 + 7) -> int:
    """Compute polynomial rolling hash for a sequence of tokens."""
    h = 0
    for t in tokens:
        h = (h * base + hash(t) % mod) % mod
    return h


def _window_hash(lines: list[str], start: int, length: int) -> int:
    """Hash a window of normalized lines."""
    window = tuple(_normalize_line(lines[i]) for i in range(start, start + length))
    return hash(window)


def _find_duplicates(
    file_a: str,
    lines_a: list[str],
    file_b: str,
    lines_b: list[str],
    min_lines: int,
) -> list[tuple[int, int, int, int, int]]:
    """
    Find duplicate blocks between two files using hash-based window matching.

    Returns list of (start_a, end_a, start_b, end_b, line_count).
    """
    if len(lines_a) < min_lines or len(lines_b) < min_lines:
        return []

    # Build hash -> [(file, start)] for file_a
    hash_to_locs: dict[int, list[tuple[str, int]]] = {}
    for i in range(len(lines_a) - min_lines + 1):
        h = _window_hash(lines_a, i, min_lines)
        hash_to_locs.setdefault(h, []).append((file_a, i))

    # Find matches in file_b
    duplicates: list[tuple[int, int, int, int, int]] = []
    for j in range(len(lines_b) - min_lines + 1):
        h = _window_hash(lines_b, j, min_lines)
        for (_, i) in hash_to_locs.get(h, []):
            # Extend match
                k = min_lines
                while (
                    i + k < len(lines_a)
                    and j + k < len(lines_b)
                    and _normalize_line(lines_a[i + k]) == _normalize_line(lines_b[j + k])
                ):
                    k += 1
                duplicates.append((i + 1, i + k, j + 1, j + k, k))
                break  # One match per j is enough

    # Deduplicate overlapping
    if not duplicates:
        return []
    merged = sorted(duplicates, key=lambda x: (x[0], x[2]))
    result = [merged[0]]
    for (sa, ea, sb, eb, k) in merged[1:]:
        last = result[-1]
        if sa <= last[1] and sb <= last[3]:
            continue  # Overlapping, skip
        result.append((sa, ea, sb, eb, k))
    return result


def analyze_duplication(
    path: Path,
    result: ScanResult,
    config: Config,
    file_metrics: list[FileMetrics],
) -> None:
    """
    Detect duplicate code blocks across files and add to result.

    Uses line-based sliding window (not full Rabin-Karp for simplicity;
    we compare normalized lines in windows).
    """
    # Build path -> lines mapping
    path_to_lines: dict[str, list[str]] = {}
    for fm in file_metrics:
        p = Path(fm.path)
        if not p.is_absolute():
            p = path / p
        if p.exists() and fm.line_count >= config.min_file_lines_for_duplication:
            path_to_lines[str(fm.path)] = p.read_text(encoding="utf-8", errors="replace").splitlines()

    files = list(path_to_lines.keys())
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            fa, fb = files[i], files[j]
            dupes = _find_duplicates(
                fa,
                path_to_lines[fa],
                fb,
                path_to_lines[fb],
                config.min_duplicate_lines,
            )
            for (sa, ea, sb, eb, k) in dupes:
                total_a = len(path_to_lines[fa])
                total_b = len(path_to_lines[fb])
                sim = 100.0 * k / min(total_a, total_b) if min(total_a, total_b) > 0 else 0
                result.duplicate_pairs.append(
                    DuplicatePair(
                        file_a=fa,
                        file_b=fb,
                        line_start_a=sa,
                        line_end_a=ea,
                        line_start_b=sb,
                        line_end_b=eb,
                        duplicate_lines=k,
                        similarity_pct=sim,
                    )
                )
                result.findings.append(
                    Finding(
                        kind=FindingKind.DUPLICATION,
                        severity=Severity.MEDIUM if k < 20 else Severity.HIGH,
                        file_path=fa,
                        message=f"Duplicate block of {k} lines with {fb} (L{sb}-{eb})",
                        line_start=sa,
                        line_end=ea,
                        metric_value=k,
                        extra={"file_b": fb, "line_start_b": sb, "line_end_b": eb},
                    )
                )
