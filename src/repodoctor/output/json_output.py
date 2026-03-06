"""JSON export for RepoDoctor scan results."""

import json
from datetime import datetime
from pathlib import Path

from repodoctor import __version__
from repodoctor.models import ScanResult
from repodoctor.scoring import get_severity_label


def format_json(result: ScanResult) -> str:
    """Serialize scan result to JSON string."""
    data = {
        "metadata": {
            "version": __version__,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "root_path": str(result.root_path),
        },
        "score": {
            "debt_score": result.debt_score,
            "severity": get_severity_label(result.debt_score or 0),
            "sub_scores": result.sub_scores,
        },
        "summary": {
            "files_scanned": len(result.file_metrics),
            "findings_count": len(result.findings),
            "duplicate_pairs_count": len(result.duplicate_pairs),
            "circular_dependencies_count": len(result.circular_dependencies),
        },
        "findings": [
            {
                "kind": f.kind.value,
                "severity": f.severity.value,
                "file_path": str(f.file_path),
                "message": f.message,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "metric_value": f.metric_value,
                "extra": f.extra,
            }
            for f in result.findings
        ],
        "duplicate_pairs": [
            {
                "file_a": str(dp.file_a),
                "file_b": str(dp.file_b),
                "line_start_a": dp.line_start_a,
                "line_end_a": dp.line_end_a,
                "line_start_b": dp.line_start_b,
                "line_end_b": dp.line_end_b,
                "duplicate_lines": dp.duplicate_lines,
                "similarity_pct": dp.similarity_pct,
            }
            for dp in result.duplicate_pairs
        ],
        "circular_dependencies": [
            {"modules": cd.modules, "path": cd.path}
            for cd in result.circular_dependencies
        ],
        "git_metrics": None,
    }
    if result.git_metrics:
        data["git_metrics"] = {
            "churn_by_file": result.git_metrics.churn_by_file,
            "hotspots": result.git_metrics.hotspots,
            "contributor_count_by_file": result.git_metrics.contributor_count_by_file,
        }
    return json.dumps(data, indent=2)


def write_json(result: ScanResult, output_path: Path) -> None:
    """Write JSON report to file."""
    output_path.write_text(format_json(result), encoding="utf-8")
