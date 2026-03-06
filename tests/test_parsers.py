"""Tests for Tree-sitter parser."""

from pathlib import Path

from repodoctor.parsers.treesitter import detect_language, parse_file


def test_detect_language() -> None:
    """Language detection from extension."""
    assert detect_language(Path("foo.py")) == "python"
    assert detect_language(Path("bar.js")) == "javascript"
    assert detect_language(Path("baz.ts")) == "typescript"
    assert detect_language(Path("qux.go")) is None


def test_parse_python_file(temp_dir: Path) -> None:
    """Parse Python file extracts functions and complexity."""
    p = temp_dir / "test.py"
    p.write_text('''
def hello():
    print("hi")

def complex():
    if x:
        for i in range(10):
            while i > 0:
                pass
''')
    result = parse_file(p)
    assert result is not None
    assert result["language"] == "python"
    assert len(result["functions"]) == 2
    assert result["functions"][0]["name"] == "hello"
    assert result["functions"][1]["complexity"] >= 4  # if, for, while
