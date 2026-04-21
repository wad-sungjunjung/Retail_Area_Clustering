from dataclasses import dataclass
from pathlib import Path


@dataclass
class SmallBusinessCollector:
    """소상공인시장진흥공단 상가업소 CSV 로더."""

    source_path: Path

    def load(self):
        raise NotImplementedError
