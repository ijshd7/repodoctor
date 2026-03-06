"""Base analyzer interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from repodoctor.config import Config
from repodoctor.models import ScanResult


class BaseAnalyzer(ABC):
    """Abstract base class for all analyzers."""

    @abstractmethod
    def analyze(self, path: Path, result: ScanResult, config: Config) -> None:
        """
        Analyze the given path and update the ScanResult.

        Args:
            path: Root directory to analyze
            result: ScanResult to update with findings
            config: Configuration with thresholds
        """
        ...
