"""카카오 POI count → 동별 정규화 feature.

두 가지 신호를 함께 제공:
  (a) percentile rank(= 동이 얼마나 번화한가)
  (b) 카테고리 비중(= 같은 번화가 내에서도 이 카테고리가 얼마나 특징적인가)

번화가는 모든 POI 카테고리가 절대치로 높기 때문에 (a) 단독으로는 변별이 안 됨.
(b) 를 주 신호로, (a) 는 보조·fallback 으로 사용한다.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


REGION_KEYS = ["sido", "sigungu", "eupmyeondong"]

KAKAO_RAW_MAP = {
    "kakao_SC4_count": "school",
    "kakao_AT4_count": "tourist_spot",
    "kakao_SW8_count": "subway_station",
    "kakao_BK9_count": "bank",
    "kakao_AD5_count": "accommodation",
    "kakao_CT1_count": "culture_facility",
    "kakao_AC5_count": "academy",
    "kakao_HP8_count": "hospital",
    "kakao_CS2_count": "convenience_store",
}


def build_kakao_features(
    poi_path: Path,
    kw_path: Path | None = None,
    kw3_path: Path | None = None,
    univ_sc4_path: Path | None = None,
    univ_2km_path: Path | None = None,
) -> pd.DataFrame:
    df = pd.read_parquet(poi_path)
    out = df[REGION_KEYS].copy()

    # 원본 count
    raw_cols = list(KAKAO_RAW_MAP.keys())
    for c in raw_cols:
        if c not in df.columns:
            df[c] = 0
        df[c] = df[c].fillna(0).astype(float)

    total_kakao = df[raw_cols].sum(axis=1).replace(0, pd.NA)

    # (a) density rank (동의 번화도 프록시)
    for src, base in KAKAO_RAW_MAP.items():
        out[f"{base}_density"] = df[src].rank(pct=True).fillna(0.0)

    # (b) 비중 → percentile rank (번화가 내 차별 신호)
    for src, base in KAKAO_RAW_MAP.items():
        share = (df[src] / total_kakao).fillna(0.0)
        out[f"{base}_share"] = share.rank(pct=True).fillna(0.0)

    # 종합 번화도 (어떤 유형도 아님 지표: 이 값이 낮으면 GENERAL 후보)
    out["kakao_total_rank"] = df[raw_cols].sum(axis=1).rank(pct=True).fillna(0.0)

    # keyword 기반 특화 feature (Phase 2.1)
    if kw_path is not None and kw_path.exists():
        kw = pd.read_parquet(kw_path)
        out = out.merge(kw, on=REGION_KEYS, how="left")
        for col, base in [
            ("kakao_kw_아파트", "apartment_count"),
            ("kakao_kw_백화점", "department_store_count"),
        ]:
            if col in out.columns:
                vals = out[col].fillna(0).astype(float)
                out[f"{base}_rank"] = vals.rank(pct=True).fillna(0.0)
                out = out.drop(columns=[col])
        # 대학교 keyword는 category filter가 없어 부정확 → drop
        if "kakao_kw_대학교" in out.columns:
            out = out.drop(columns=["kakao_kw_대학교"])

    # 대학교 정확 카운트 (3km SC4 필터)
    if univ_sc4_path is not None and univ_sc4_path.exists():
        uni = pd.read_parquet(univ_sc4_path)
        out = out.merge(uni, on=REGION_KEYS, how="left")
        vals = out["kakao_univ_sc4"].fillna(0).astype(float)
        out["university_count_rank"] = vals.rank(pct=True).fillna(0.0)
        out = out.drop(columns=["kakao_univ_sc4"])

    # 대학교 2km (CAMPUS 엄격 판별용)
    if univ_2km_path is not None and univ_2km_path.exists():
        u2 = pd.read_parquet(univ_2km_path)
        out = out.merge(u2, on=REGION_KEYS, how="left")
        vals = out["kakao_univ_sc4_2km"].fillna(0).astype(float)
        out["university_2km_rank"] = vals.rank(pct=True).fillna(0.0)
        # binary flag: 2km 내 대학 2개 이상이면 1
        out["university_2km_has_campus"] = (vals >= 2).astype(float)
        out = out.drop(columns=["kakao_univ_sc4_2km"])

    # keyword 기반 특화 feature (Phase 3) — NIGHTLIFE / DATE_TRENDY 보강
    if kw3_path is not None and kw3_path.exists():
        kw3 = pd.read_parquet(kw3_path)
        out = out.merge(kw3, on=REGION_KEYS, how="left")
        for col, base in [
            ("kakao_kw_클럽", "club_count"),
            ("kakao_kw_바", "bar_count"),
            ("kakao_kw_포차", "pocha_count"),
            ("kakao_kw_브런치", "brunch_count"),
            ("kakao_kw_디저트", "dessert_count"),
        ]:
            if col in out.columns:
                vals = out[col].fillna(0).astype(float)
                out[f"{base}_rank"] = vals.rank(pct=True).fillna(0.0)
                out = out.drop(columns=[col])
    return out
