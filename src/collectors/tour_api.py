from dataclasses import dataclass
from pathlib import Path


@dataclass
class TourApiCollector:
    api_key: str

    def collect(self, area_codes, out_dir: Path):
        raise NotImplementedError
