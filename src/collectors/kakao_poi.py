"""카카오 로컬 API — 반경 기반 POI 카운트 수집기.

각 동의 중심 좌표(lon/lat)를 기준으로 반경 radius_m 내 카테고리별 POI 수를
`meta.total_count` 필드로 받아 기록한다. 요청 1건으로 해당 카테고리 total 을 얻는다.

체크포인트는 JSONL 로 누적 저장하여 중단/재개 가능.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


CATEGORY_CODES = {
    "SC4": "학교",
    "AT4": "관광명소",
    "SW8": "지하철역",
    "BK9": "은행",
    "AD5": "숙박",
    "CT1": "문화시설",
    "AC5": "학원",
    "HP8": "병원",
    "CS2": "편의점",
}


@dataclass
class KakaoPoiCollector:
    api_key: str
    radius_m: int = 1000
    rate_limit_per_sec: float = 10.0
    timeout_s: float = 8.0
    max_retries: int = 3
    _last_call: float = field(default=0.0, init=False)

    BASE = "https://dapi.kakao.com/v2/local/search/category.json"

    def _throttle(self) -> None:
        min_gap = 1.0 / max(self.rate_limit_per_sec, 0.1)
        dt = time.time() - self._last_call
        if dt < min_gap:
            time.sleep(min_gap - dt)
        self._last_call = time.time()

    def count(self, category: str, lon: float, lat: float) -> int | None:
        params = {
            "category_group_code": category,
            "x": f"{lon}",
            "y": f"{lat}",
            "radius": str(self.radius_m),
            "size": "1",
            "page": "1",
        }
        headers = {"Authorization": f"KakaoAK {self.api_key}"}
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                r = requests.get(self.BASE, params=params, headers=headers,
                                 timeout=self.timeout_s)
                if r.status_code == 200:
                    return int(r.json().get("meta", {}).get("total_count", 0))
                if r.status_code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if r.status_code in (400, 401, 403):
                    return None  # 영구 실패
            except requests.RequestException:
                time.sleep(0.5 * (attempt + 1))
        return None

    def collect_all(
        self,
        regions: pd.DataFrame,
        categories: Iterable[str],
        checkpoint_path: Path,
    ) -> pd.DataFrame:
        """regions: columns [sido, sigungu, eupmyeondong, lon, lat]"""
        categories = list(categories)
        done = _load_checkpoint(checkpoint_path)
        results = list(done.values())
        total = len(regions) * len(categories)
        completed = sum(len(v) - 3 for v in done.values())  # 3 region keys
        print(f"[kakao] targets={total:,}, already_done={completed:,}")

        with open(checkpoint_path, "a", encoding="utf-8") as cp:
            for idx, row in regions.iterrows():
                key = (row["sido"], row["sigungu"], row["eupmyeondong"])
                existing = done.get(key, {
                    "sido": row["sido"], "sigungu": row["sigungu"],
                    "eupmyeondong": row["eupmyeondong"],
                })
                missing = [c for c in categories if c not in existing]
                if not missing:
                    continue
                if pd.isna(row.get("lon")) or pd.isna(row.get("lat")):
                    # 좌표 없음 — 카테고리 모두 결측으로 저장
                    for c in missing:
                        existing[c] = None
                    cp.write(json.dumps(existing, ensure_ascii=False) + "\n")
                    cp.flush()
                    done[key] = existing
                    continue
                for c in missing:
                    n = self.count(c, float(row["lon"]), float(row["lat"]))
                    existing[c] = n
                    completed += 1
                cp.write(json.dumps(existing, ensure_ascii=False) + "\n")
                cp.flush()
                done[key] = existing
                if (idx + 1) % 50 == 0:
                    print(f"[kakao] progress {idx+1}/{len(regions)} dongs "
                          f"(~{completed:,}/{total:,} calls)")
        return _checkpoint_to_df(done, categories)


def _load_checkpoint(path: Path) -> dict:
    out: dict = {}
    if not path.exists():
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (rec.get("sido"), rec.get("sigungu"), rec.get("eupmyeondong"))
            # 뒤에 쓰인 줄이 최신
            out[key] = rec
    return out


def _checkpoint_to_df(done: dict, categories: list[str]) -> pd.DataFrame:
    rows = []
    for key, rec in done.items():
        row = {"sido": rec["sido"], "sigungu": rec["sigungu"],
               "eupmyeondong": rec["eupmyeondong"]}
        for c in categories:
            v = rec.get(c)
            row[f"kakao_{c}_count"] = (int(v) if v is not None else 0)
        rows.append(row)
    return pd.DataFrame(rows)
