"""HTML report generation for RepoDoctor scan results."""

from pathlib import Path

from jinja2 import Template

from repodoctor import __version__
from repodoctor.models import ScanResult
from repodoctor.scoring import get_severity_label

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RepoDoctor Report - {{ root_path }}</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #4ec9b0; }
        .score-panel { background: #252526; border-radius: 8px; padding: 24px; margin: 20px 0; }
        .score-value { font-size: 2.5rem; font-weight: bold; }
        .score-value.healthy { color: #4ec9b0; }
        .score-value.moderate { color: #dcdcaa; }
        .score-value.concerning { color: #ce9178; }
        .score-value.critical { color: #f48771; }
        .sub-scores { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 16px; }
        .sub-score { background: #333; padding: 12px 16px; border-radius: 6px; }
        .sub-score span { color: #9cdcfe; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #404040; }
        th { background: #2d2d2d; color: #9cdcfe; }
        tr:hover { background: #2d2d2d; }
        .severity-low { color: #808080; }
        .severity-medium { color: #dcdcaa; }
        .severity-high { color: #ce9178; }
        .severity-critical { color: #f48771; }
        .meta { color: #6a9955; font-size: 0.9rem; margin-bottom: 20px; }
        section { margin: 24px 0; }
        h2 { color: #4ec9b0; border-bottom: 1px solid #404040; padding-bottom: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>RepoDoctor Report</h1>
        <p class="meta">Version {{ version }} | Scanned: {{ root_path }} | {{ timestamp }}</p>

        <div class="score-panel">
            <h2>Technical Debt Score</h2>
            <div class="score-value {{ severity_class }}">{{ debt_score }}/100</div>
            <p>{{ severity_label }}</p>
            <div class="sub-scores">
                {% for name, value in sub_scores.items() %}
                <div class="sub-score"><span>{{ name }}:</span> {{ "%.1f"|format(value) }}</div>
                {% endfor %}
            </div>
        </div>

        <section>
            <h2>Summary</h2>
            <p>Files scanned: {{ files_count }} | Findings: {{ findings_count }} | Duplicates: {{ dup_count }} | Circular deps: {{ circ_count }}</p>
        </section>

        {% if circular_dependencies %}
        <section>
            <h2>Circular Dependencies</h2>
            <table>
                <thead><tr><th>Cycle</th></tr></thead>
                <tbody>
                {% for cd in circular_dependencies %}
                <tr><td>{{ cd.path }}</td></tr>
                {% endfor %}
                </tbody>
            </table>
        </section>
        {% endif %}

        {% if duplicate_pairs %}
        <section>
            <h2>Duplication</h2>
            <table>
                <thead><tr><th>File A</th><th>Lines</th><th>File B</th><th>Lines</th><th>Duplicate Lines</th></tr></thead>
                <tbody>
                {% for dp in duplicate_pairs %}
                <tr>
                    <td>{{ dp.file_a }}</td>
                    <td>L{{ dp.line_start_a }}-{{ dp.line_end_a }}</td>
                    <td>{{ dp.file_b }}</td>
                    <td>L{{ dp.line_start_b }}-{{ dp.line_end_b }}</td>
                    <td>{{ dp.duplicate_lines }}</td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </section>
        {% endif %}

        {% for kind, items in findings_by_kind.items() %}
        {% if items %}
        <section>
            <h2>{{ kind_labels.get(kind, kind) }}</h2>
            <table>
                <thead><tr><th>File</th><th>Location</th><th>Message</th><th>Severity</th></tr></thead>
                <tbody>
                {% for f in items %}
                <tr>
                    <td>{{ f.file_path }}</td>
                    <td>{% if f.line_start %}L{{ f.line_start }}{% if f.line_end and f.line_end != f.line_start %}-{{ f.line_end }}{% endif %}{% endif %}</td>
                    <td>{{ f.message }}</td>
                    <td class="severity-{{ f.severity.value }}">{{ f.severity.value }}</td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </section>
        {% endif %}
        {% endfor %}
    </div>
</body>
</html>
"""

KIND_LABELS = {
    "long_function": "Long Functions",
    "high_complexity": "High Complexity",
    "large_file": "Large Files",
    "deep_nesting": "Deep Nesting",
    "duplication": "Duplication",
    "circular_dependency": "Circular Dependencies",
    "risky_module": "Risky Modules",
    "hotspot": "Git Hotspots",
}


def _group_findings(findings: list) -> dict:
    """Group findings by kind."""
    groups: dict = {}
    for f in findings:
        k = f.kind.value
        groups.setdefault(k, []).append(f)
    return groups


def format_html(result: ScanResult, timestamp: str = "") -> str:
    """Render HTML report string."""
    from datetime import datetime
    ts = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    severity = get_severity_label(result.debt_score or 0)
    severity_class = severity.lower()
    findings_by_kind = _group_findings(result.findings)
    return Template(HTML_TEMPLATE).render(
        version=__version__,
        root_path=str(result.root_path),
        timestamp=ts,
        debt_score=result.debt_score or 0,
        severity_label=severity,
        severity_class=severity_class,
        sub_scores=result.sub_scores,
        files_count=len(result.file_metrics),
        findings_count=len(result.findings),
        dup_count=len(result.duplicate_pairs),
        circ_count=len(result.circular_dependencies),
        circular_dependencies=result.circular_dependencies,
        duplicate_pairs=result.duplicate_pairs,
        findings_by_kind=findings_by_kind,
        kind_labels=KIND_LABELS,
    )


def write_html(result: ScanResult, output_path: Path) -> None:
    """Write HTML report to file."""
    output_path.write_text(format_html(result), encoding="utf-8")
