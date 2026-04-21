from dataclasses import dataclass
from pathlib import Path


@dataclass
class AptHousingCollector:
    """국토부 공동주택 공시 CSV 로더 → 동별 아파트 세대수 집계."""

    source_path: Path

    def load(self):
        raise NotImplementedError
