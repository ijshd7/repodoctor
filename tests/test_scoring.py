"""Tests for scoring engine."""

from pathlib import Path

from repodoctor.models import ScanResult
from repodoctor.scoring import compute_debt_score, get_severity_label


def test_get_severity_label() -> None:
    """Severity labels match score ranges."""
    assert get_severity_label(0) == "Healthy"
    assert get_severity_label(25) == "Healthy"
    assert get_severity_label(26) == "Moderate"
    assert get_severity_label(50) == "Moderate"
    assert get_severity_label(51) == "Concerning"
    assert get_severity_label(75) == "Concerning"
    assert get_severity_label(76) == "Critical"
    assert get_severity_label(100) == "Critical"


def test_compute_debt_score() -> None:
    """Score is computed and in 0-100 range."""
    result = ScanResult(root_path=Path("."))
    compute_debt_score(result)
    assert result.debt_score is not None
    assert 0 <= result.debt_score <= 100
    assert "complexity" in result.sub_scores
    assert "duplication" in result.sub_scores
    assert "dependencies" in result.sub_scores
    assert "git" in result.sub_scores
