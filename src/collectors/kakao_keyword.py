"""카카오 키워드 검색 — 반경 내 특정 키워드 POI 수 집계.

용도: `SC4 학교`는 초·중·고 + 대학을 모두 포함해 CAMPUS 변별이 어려움.
     keyword="대학교" 검색으로 대학교만 분리 수집.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


@dataclass
class KakaoKeywordCollector:
    api_key: str
    radius_m: int = 3000            # 대학가는 3km 반경
    rate_limit_per_sec: float = 10.0
    timeout_s: float = 8.0
    max_retries: int = 3
    _last_call: float = field(default=0.0, init=False)

    BASE = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def _throttle(self) -> None:
        min_gap = 1.0 / max(self.rate_limit_per_sec, 0.1)
        dt = time.time() - self._last_call
        if dt < min_gap:
            time.sleep(min_gap - dt)
        self._last_call = time.time()

    def count(self, keyword: str, lon: float, lat: float,
              category_group_code: str | None = None) -> int | None:
        params = {
            "query": keyword,
            "x": f"{lon}",
            "y": f"{lat}",
            "radius": str(self.radius_m),
            "size": "1",
            "page": "1",
        }
        if category_group_code:
            params["category_group_code"] = category_group_code
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
                    return None
            except requests.RequestException:
                time.sleep(0.5 * (attempt + 1))
        return None

    def collect_all(
        self,
        regions: pd.DataFrame,
        keywords: Iterable[str],
        checkpoint_path: Path,
    ) -> pd.DataFrame:
        """regions: columns [sido, sigungu, eupmyeondong, lon, lat]"""
        keywords = list(keywords)
        done = _load_checkpoint(checkpoint_path)
        total = len(regions) * len(keywords)
        completed = sum(len([k for k in rec.keys() if k in keywords]) for rec in done.values())
        print(f"[kakao-kw] targets={total:,}, already_done={completed:,}")

        with open(checkpoint_path, "a", encoding="utf-8") as cp:
            for idx, row in regions.iterrows():
                key = (row["sido"], row["sigungu"], row["eupmyeondong"])
                existing = done.get(key, {
                    "sido": row["sido"], "sigungu": row["sigungu"],
                    "eupmyeondong": row["eupmyeondong"],
                })
                missing = [k for k in keywords if k not in existing]
                if not missing:
                    continue
                if pd.isna(row.get("lon")) or pd.isna(row.get("lat")):
                    for k in missing:
                        existing[k] = None
                else:
                    for k in missing:
                        existing[k] = self.count(k, float(row["lon"]), float(row["lat"]))
                        completed += 1
                cp.write(json.dumps(existing, ensure_ascii=False) + "\n")
                cp.flush()
                done[key] = existing
                if (idx + 1) % 100 == 0:
                    print(f"[kakao-kw] {idx+1}/{len(regions)} dongs (~{completed:,}/{total:,})")
        return _to_df(done, keywords)


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
            out[key] = rec
    return out


def _to_df(done: dict, keywords: list[str]) -> pd.DataFrame:
    rows = []
    for key, rec in done.items():
        row = {"sido": rec["sido"], "sigungu": rec["sigungu"],
               "eupmyeondong": rec["eupmyeondong"]}
        for k in keywords:
            v = rec.get(k)
            row[f"kakao_kw_{k}"] = (int(v) if v is not None else 0)
        rows.append(row)
    return pd.DataFrame(rows)
