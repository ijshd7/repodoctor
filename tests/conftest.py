"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_python_file(temp_dir: Path) -> Path:
    """Create a sample Python file for testing."""
    path = temp_dir / "sample.py"
    path.write_text(
        '''
def hello():
    print("hello")

def complex_func():
    if True:
        for i in range(10):
            while i > 0:
                if i % 2 == 0:
                    pass
'''
    )
    return path
