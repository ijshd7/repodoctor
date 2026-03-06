"""Git analyzer: commit churn, hotspots, contributor spread."""

from pathlib import Path

from repodoctor.config import Config
from repodoctor.models import Finding, FindingKind, GitMetrics, ScanResult, Severity
from repodoctor.utils import resolve_relative_path


def _collect_churn_and_contributors(repo, max_commits: int) -> tuple[dict[str, int], dict[str, set[str]]]:
    """Collect churn and contributor stats from commit history."""
    churn_by_file: dict[str, int] = {}
    contributor_by_file: dict[str, set[str]] = {}
    try:
        commits = list(repo.iter_commits(max_count=max_commits))
    except Exception:
        return churn_by_file, contributor_by_file

    for commit in commits:
        try:
            author = commit.author.email or str(commit.author)
            for item in commit.stats.files:
                churn_by_file[item] = churn_by_file.get(item, 0) + 1
                contributor_by_file.setdefault(item, set()).add(author)
        except Exception:
            continue
    return churn_by_file, contributor_by_file


def _normalize_paths(
    churn_by_file: dict[str, int],
    contributor_by_file: dict[str, set[str]],
    repo_root: Path,
) -> tuple[dict[str, int], dict[str, int]]:
    """Normalize file paths to be relative to repo root."""
    rel_churn = {resolve_relative_path(f, repo_root): c for f, c in churn_by_file.items()}
    contributor_count = {
        resolve_relative_path(f, repo_root): len(s) for f, s in contributor_by_file.items()
    }
    return rel_churn, contributor_count


def _find_hotspots(
    rel_churn: dict[str, int],
    file_metrics: list,
    churn_threshold: int = 5,
    lines_threshold: int = 100,
    max_candidates: int = 50,
) -> list[str]:
    """Find files that are both high-churn and high-complexity."""
    file_line_count = {}
    for fm in file_metrics:
        fp = str(fm.path) if hasattr(fm, "path") else fm[0]
        lc = fm.line_count if hasattr(fm, "line_count") else fm[1]
        file_line_count[fp] = lc

    hotspots: list[str] = []
    for f, churn in sorted(rel_churn.items(), key=lambda x: -x[1])[:max_candidates]:
        lines = file_line_count.get(f, 0)
        if churn >= churn_threshold and lines >= lines_threshold:
            hotspots.append(f)
    return hotspots


def analyze_git(
    path: Path,
    result: ScanResult,
    config: Config,
    file_metrics: list,
) -> None:
    """
    Analyze Git history for churn, hotspots, and contributor spread.

    file_metrics: list of (file_path, line_count) for complexity cross-reference.
    """
    try:
        import git
    except ImportError:
        return

    try:
        repo = git.Repo(path, search_parent_directories=True)
    except Exception:
        return

    churn_by_file, contributor_by_file = _collect_churn_and_contributors(
        repo, config.max_commits_for_churn
    )
    repo_root = Path(repo.working_dir)
    rel_churn, contributor_count = _normalize_paths(
        churn_by_file, contributor_by_file, repo_root
    )
    hotspots = _find_hotspots(rel_churn, file_metrics)

    result.git_metrics = GitMetrics(
        churn_by_file=rel_churn,
        hotspots=hotspots[:20],
        contributor_count_by_file=contributor_count,
    )

    for f in hotspots[:10]:
        churn = rel_churn.get(f, 0)
        result.findings.append(
            Finding(
                kind=FindingKind.HOTSPOT,
                severity=Severity.HIGH if churn >= 10 else Severity.MEDIUM,
                file_path=f,
                message=f"Hotspot: high churn ({churn} commits) and complexity",
                metric_value=churn,
                extra={"churn": churn},
            )
        )
