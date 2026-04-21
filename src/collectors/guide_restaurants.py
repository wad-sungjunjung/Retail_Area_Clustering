from dataclasses import dataclass
from pathlib import Path


@dataclass
class GuideRestaurantCollector:
    """미쉐린·블루리본 등 공개 가이드 크롤러."""

    out_dir: Path

    def crawl_michelin(self):
        raise NotImplementedError

    def crawl_bluer(self):
        raise NotImplementedError
