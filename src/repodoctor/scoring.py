"""Technical debt scoring engine."""

from repodoctor.models import ScanResult


def compute_debt_score(result: ScanResult) -> None:
    """
    Compute weighted technical debt score (0-100) and sub-scores.
    Mutates result.debt_score and result.sub_scores.
    """
    sub_scores: dict[str, float] = {}

    # Complexity sub-score (30%)
    total_lines = sum(fm.line_count for fm in result.file_metrics)
    total_functions = sum(len(fm.functions) for fm in result.file_metrics)
    complexity_findings = [f for f in result.findings if f.kind.value in (
        "long_function", "high_complexity", "large_file", "deep_nesting"
    )]
    avg_complexity = 0.0
    if total_functions > 0:
        all_complexities = []
        for fm in result.file_metrics:
            for func in fm.functions:
                all_complexities.append(func.get("complexity", 1))
        avg_complexity = sum(all_complexities) / len(all_complexities) if all_complexities else 0
    long_func_ratio = len([f for f in complexity_findings if f.kind.value == "long_function"]) / max(total_functions, 1)
    large_file_ratio = len([f for f in complexity_findings if f.kind.value == "large_file"]) / max(len(result.file_metrics), 1)
    complexity_raw = (avg_complexity / 10.0) * 40 + long_func_ratio * 30 + large_file_ratio * 30
    sub_scores["complexity"] = min(100.0, complexity_raw)

    # Duplication sub-score (20%)
    dup_lines = sum(dp.duplicate_lines for dp in result.duplicate_pairs)
    dup_ratio = dup_lines / max(total_lines, 1)
    sub_scores["duplication"] = min(100.0, dup_ratio * 500)  # 20% dup = 100

    # Dependency sub-score (25%)
    cycle_count = len(result.circular_dependencies)
    dep_findings = [f for f in result.findings if f.kind.value in ("circular_dependency", "risky_module")]
    sub_scores["dependencies"] = min(100.0, cycle_count * 20 + len(dep_findings) * 5)

    # Git churn sub-score (25%) - 0 if no Git
    if result.git_metrics and result.git_metrics.hotspots:
        hotspot_count = len(result.git_metrics.hotspots)
        max_churn = max(result.git_metrics.churn_by_file.values(), default=0)
        sub_scores["git"] = min(100.0, hotspot_count * 5 + min(max_churn * 2, 50))
    else:
        sub_scores["git"] = 0.0

    # Weighted total (redistribute git weight if skipped)
    weights = {"complexity": 0.30, "duplication": 0.20, "dependencies": 0.25, "git": 0.25}
    if sub_scores["git"] == 0:
        weights = {"complexity": 0.40, "duplication": 0.25, "dependencies": 0.35, "git": 0.0}
    total = sum(sub_scores[k] * w for k, w in weights.items())
    result.debt_score = round(total, 1)
    result.sub_scores = sub_scores


def get_severity_label(score: float) -> str:
    """Return severity label for debt score."""
    if score <= 25:
        return "Healthy"
    if score <= 50:
        return "Moderate"
    if score <= 75:
        return "Concerning"
    return "Critical"
