"""Tests for complexity analyzer."""

from pathlib import Path

import pytest

from repodoctor.analyzers.complexity import analyze_complexity
from repodoctor.config import get_default_config
from repodoctor.models import FileMetrics, FindingKind, ScanResult


def test_analyze_complexity_long_function(sample_python_file: Path, temp_dir: Path) -> None:
    """Long function should be flagged."""
    # Create a file with a long function
    long_file = temp_dir / "long_func.py"
    long_file.write_text("def foo():\n" + "    pass\n" * 60)
    from repodoctor.parsers.treesitter import parse_file
    parsed = parse_file(long_file)
    assert parsed
    fm = FileMetrics(
        path=str(long_file),
        line_count=parsed["line_count"],
        functions=parsed["functions"],
        imports=[],
        language="python",
    )
    result = ScanResult(root_path=temp_dir, file_metrics=[fm])
    config = get_default_config()
    config.max_function_lines = 50
    analyze_complexity(temp_dir, result, config, [fm])
    long_findings = [f for f in result.findings if f.kind == FindingKind.LONG_FUNCTION]
    assert len(long_findings) >= 1
