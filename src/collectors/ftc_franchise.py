from dataclasses import dataclass
from pathlib import Path


@dataclass
class FranchiseCollector:
    """공정거래위원회 가맹사업정보 CSV 로더."""

    source_path: Path

    def load(self):
        raise NotImplementedError
