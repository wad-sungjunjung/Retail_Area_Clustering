from dataclasses import dataclass
from pathlib import Path


@dataclass
class UniversityCollector:
    """대학알리미 대학·재학생 수 로더."""

    source_path: Path

    def load(self):
        raise NotImplementedError
