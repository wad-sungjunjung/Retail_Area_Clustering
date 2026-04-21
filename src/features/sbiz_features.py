"""소상공인시장진흥공단_상가(상권)정보 CSV → 동별 feature store.

CSV 컬럼:
  시도명, 시군구명, 행정동명,
  상권업종대분류명, 상권업종중분류명, 상권업종소분류명,
  상호명, 지점명, 경도, 위도 ...

동 단위로 집계한 뒤 전국 quantile rank 로 0~1 정규화한다.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

REGION_KEYS = ["sido", "sigungu", "eupmyeondong"]

USECOLS = [
    "시도명", "시군구명", "행정동명",
    "상권업종대분류명", "상권업종중분류명", "상권업종소분류명",
    "상호명", "지점명", "경도", "위도",
]

# 소분류 수준의 업종 버킷 (실제 CSV 소분류명과 정확 일치 필요)
PREMIUM_SO = {
    "경양식",             # 이태리·프렌치 양식
    "일식 회/초밥",        # 스시·사시미
    "소고기 구이/찜",       # 한우
    "복 요리 전문",
}
# 백반/한정식, 횟집은 제외 (지방 혼선 방지)
LOWPRICE_SO = {
    "김밥/만두/분식", "치킨", "빵/도넛", "피자", "버거",
    "떡/한과", "아이스크림/빙수", "토스트/샌드위치/샐러드",
    "그 외 기타 간이 음식점",
    "일식 카레/돈가스/덮밥",  # 캐주얼 일식
}
IZAKAYA_PUB_SO = {"요리 주점", "생맥주 전문"}
ENTERTAINMENT_SO = {"일반 유흥 주점", "무도 유흥 주점"}

# 중분류 수준
KOREAN_MID = {"한식"}
CAFE_MID = {"비알코올"}
ALCOHOL_MID = {"주점"}
FOREIGN_MID = {"일식", "중식", "서양식", "동남아시아"}

# 대형 프랜차이즈 상호명(지점명 있는 경우 포함) — 대표 브랜드
FRANCHISE_BRANDS = [
    "스타벅스", "투썸플레이스", "이디야", "메가엠지씨커피", "메가커피",
    "커피빈", "할리스", "빽다방", "컴포즈커피", "폴바셋", "공차",
    "맥도날드", "버거킹", "롯데리아", "맘스터치", "KFC", "파파이스",
    "써브웨이", "도미노피자", "피자헛", "미스터피자", "파파존스",
    "교촌치킨", "BBQ", "BHC", "굽네치킨", "푸라닭", "네네치킨",
    "본죽", "김밥천국", "바르다김선생", "고봉민김밥",
    "베스킨라빈스", "배스킨라빈스", "던킨", "파리바게뜨", "뚜레쥬르",
    "올리브영", "다이소", "세븐일레븐", "CU", "GS25", "이마트24",
    "신전떡볶이", "죠스떡볶이",
    "놀부부대찌개", "원할머니보쌈", "아웃백", "빕스", "애슐리",
]


def _norm_sido(name: str | float) -> str:
    if not isinstance(name, str):
        return ""
    return name.strip()


def _split_sigungu(sido: str, sigungu: str) -> str:
    """'성남시 분당구' 처럼 이미 구 포함된 경우는 그대로, 세종 케이스는 공백 정리."""
    if not isinstance(sigungu, str):
        return ""
    s = sigungu.strip()
    if sido == s:
        return s
    return s


def _is_franchise_vec(names: pd.Series, branches: pd.Series) -> pd.Series:
    has_branch = branches.notna() & (branches.astype("string").str.strip().str.len() > 0)
    name_str = names.fillna("").astype(str)
    pattern = "|".join(re.escape(b) for b in FRANCHISE_BRANDS)
    has_brand = name_str.str.contains(pattern, regex=True, na=False)
    return has_branch | has_brand


def _aggregate_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Per-(시도, 시군구, 행정동) 집계."""
    df = df.copy()
    df["시도명"] = df["시도명"].map(_norm_sido)
    df["is_food"] = df["상권업종대분류명"] == "음식"
    df["is_korean"] = df["상권업종중분류명"].isin(KOREAN_MID)
    df["is_cafe"] = df["상권업종중분류명"].isin(CAFE_MID)
    df["is_alcohol"] = df["상권업종중분류명"].isin(ALCOHOL_MID)
    df["is_foreign"] = df["상권업종중분류명"].isin(FOREIGN_MID)
    df["is_izakaya_pub"] = df["상권업종소분류명"].isin(IZAKAYA_PUB_SO)
    df["is_entertainment"] = df["상권업종소분류명"].isin(ENTERTAINMENT_SO)
    df["is_premium"] = df["상권업종소분류명"].isin(PREMIUM_SO)
    df["is_lowprice"] = df["상권업종소분류명"].isin(LOWPRICE_SO)
    df["is_edu"] = df["상권업종대분류명"] == "교육"
    df["is_medical"] = df["상권업종대분류명"] == "보건의료"
    df["is_accommodation"] = df["상권업종대분류명"] == "숙박"
    df["is_retail"] = df["상권업종대분류명"] == "소매"
    df["is_realestate"] = df["상권업종대분류명"] == "부동산"
    df["is_tech"] = df["상권업종대분류명"] == "과학·기술"
    df["is_franchise"] = _is_franchise_vec(df["상호명"], df["지점명"])

    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    group_cols = ["시도명", "시군구명", "행정동명"]
    agg = df.groupby(group_cols).agg(
        total=("상호명", "count"),
        food_cnt=("is_food", "sum"),
        korean_cnt=("is_korean", "sum"),
        cafe_cnt=("is_cafe", "sum"),
        alcohol_cnt=("is_alcohol", "sum"),
        foreign_cnt=("is_foreign", "sum"),
        izakaya_cnt=("is_izakaya_pub", "sum"),
        entertain_cnt=("is_entertainment", "sum"),
        premium_cnt=("is_premium", "sum"),
        lowprice_cnt=("is_lowprice", "sum"),
        edu_cnt=("is_edu", "sum"),
        medical_cnt=("is_medical", "sum"),
        accom_cnt=("is_accommodation", "sum"),
        retail_cnt=("is_retail", "sum"),
        realestate_cnt=("is_realestate", "sum"),
        tech_cnt=("is_tech", "sum"),
        franchise_cnt=("is_franchise", "sum"),
        food_franchise_cnt=("is_franchise", "sum"),
        lon=("경도", "median"),
        lat=("위도", "median"),
    ).reset_index()
    agg = agg.rename(columns={"시도명": "sido", "시군구명": "sigungu", "행정동명": "eupmyeondong"})
    return agg


def _combine_aggs(parts: list[pd.DataFrame]) -> pd.DataFrame:
    merged = pd.concat(parts, ignore_index=True)
    sum_cols = [c for c in merged.columns if c not in REGION_KEYS + ["lon", "lat"]]
    sum_part = merged.groupby(REGION_KEYS, as_index=False)[sum_cols].sum()
    coord_part = merged.groupby(REGION_KEYS, as_index=False)[["lon", "lat"]].median()
    return sum_part.merge(coord_part, on=REGION_KEYS, how="left")


def _to_features(agg: pd.DataFrame) -> pd.DataFrame:
    total = agg["total"].replace(0, np.nan)
    food = agg["food_cnt"].replace(0, np.nan)

    out = agg[REGION_KEYS].copy()
    out["lon"] = agg["lon"]
    out["lat"] = agg["lat"]
    out["total_business"] = agg["total"]

    # 비율 (/ 음식 총)
    out["premium_industry_ratio_raw"] = (agg["premium_cnt"] / food).fillna(0.0)
    out["cafe_ratio_raw"] = (agg["cafe_cnt"] / food).fillna(0.0)
    out["alcohol_industry_ratio_raw"] = (agg["alcohol_cnt"] / food).fillna(0.0)
    out["izakaya_pub_ratio_raw"] = (agg["izakaya_cnt"] / food).fillna(0.0)
    out["night_business_ratio_raw"] = (
        (agg["alcohol_cnt"] + agg["entertain_cnt"]) / food
    ).fillna(0.0)
    out["korean_traditional_ratio_raw"] = (agg["korean_cnt"] / food).fillna(0.0)
    out["low_price_industry_ratio_raw"] = (agg["lowprice_cnt"] / food).fillna(0.0)
    out["foreign_restaurant_ratio_raw"] = (agg["foreign_cnt"] / food).fillna(0.0)
    out["midlow_price_ratio_raw"] = (
        (agg["lowprice_cnt"] + agg["korean_cnt"]) / food
    ).fillna(0.0)
    out["franchise_ratio_raw"] = (agg["franchise_cnt"] / total).fillna(0.0)
    out["independent_small_ratio_raw"] = 1.0 - out["franchise_ratio_raw"]

    # 밀도 (동 내 카운트) — 후처리에서 정규화
    out["business_density_raw"] = agg["food_cnt"]  # 음식점 절대 수
    out["cafe_brunch_density_raw"] = agg["cafe_cnt"]
    out["entertainment_poi_density_raw"] = agg["entertain_cnt"] + agg["izakaya_cnt"] + agg["alcohol_cnt"]
    out["academy_density_raw"] = agg["edu_cnt"]
    out["accommodation_density_raw"] = agg["accom_cnt"]
    out["convenience_medical_density_raw"] = agg["medical_cnt"] + agg["retail_cnt"] * 0.3
    out["small_store_density_raw"] = agg["korean_cnt"] + agg["lowprice_cnt"]  # 소형 한식/분식
    out["office_poi_density_raw"] = agg["tech_cnt"] + agg["realestate_cnt"] * 0.3
    out["bank_density_raw"] = (agg["tech_cnt"] * 0.1)

    # ⬇︎ 추가 density 신호 (유형 변별력 강화용)
    out["premium_density_raw"] = agg["premium_cnt"]
    out["foreign_restaurant_density_raw"] = agg["foreign_cnt"]
    out["low_price_density_raw"] = agg["lowprice_cnt"]
    out["korean_density_raw"] = agg["korean_cnt"]

    return out


RATIO_COLS = [
    "premium_industry_ratio", "cafe_ratio", "alcohol_industry_ratio",
    "izakaya_pub_ratio", "night_business_ratio", "korean_traditional_ratio",
    "low_price_industry_ratio", "foreign_restaurant_ratio",
    "midlow_price_ratio", "franchise_ratio", "independent_small_ratio",
]

DENSITY_COLS = [
    "business_density", "cafe_brunch_density",
    "entertainment_poi_density",
    "small_store_density", "office_poi_density",
    "premium_density", "foreign_restaurant_density",
    "low_price_density", "korean_density",
]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df[REGION_KEYS + ["lon", "lat", "total_business"]].copy()
    # 비율 컬럼: 그대로 [0,1] clip (이미 비율)
    for c in RATIO_COLS:
        raw = df.get(f"{c}_raw", pd.Series(0.0, index=df.index))
        out[c] = raw.clip(0.0, 1.0)
    # 밀도 컬럼: 전국 percentile rank 로 [0,1]
    for c in DENSITY_COLS:
        raw = df.get(f"{c}_raw", pd.Series(0.0, index=df.index))
        out[c] = raw.rank(pct=True).fillna(0.0)
    # DATE_TRENDY 보조 feature: cafe_brunch_density 와 동일 base 쓰되, 별도 컬럼
    out["cafe_brunch_density"] = out["cafe_brunch_density"].astype(float)
    return out


def build_sbiz_features(csv_dir: Path, name_contains: str | None = None) -> pd.DataFrame:
    d = Path(csv_dir)
    if not d.is_dir():
        raise FileNotFoundError(f"not a dir: {csv_dir}")
    def _match(f: str) -> bool:
        if not f.endswith(".csv"):
            return False
        if name_contains is None:
            return True
        # macOS NFD 파일명 대응
        f_nfc = unicodedata.normalize("NFC", f)
        kw_nfc = unicodedata.normalize("NFC", name_contains)
        return kw_nfc in f_nfc

    csvs = sorted(str(d / f) for f in os.listdir(d) if _match(f))
    if not csvs:
        raise FileNotFoundError(f"no CSV in {csv_dir}")
    parts = []
    for p in csvs:
        if "[필독]" in p or "readme" in p.lower():
            continue
        try:
            df = pd.read_csv(p, usecols=USECOLS, low_memory=False,
                             dtype={"상호명": "string", "지점명": "string"})
        except Exception as e:
            print(f"[sbiz] skip {Path(p).name}: {e}")
            continue
        n_before = len(df)
        df = df.dropna(subset=["시도명", "시군구명", "행정동명"])
        print(f"[sbiz] {Path(p).name}: {n_before:,} rows → {len(df):,} valid")
        parts.append(_aggregate_frame(df))
    agg = _combine_aggs(parts)
    raw_feat = _to_features(agg)
    return _normalize(raw_feat)
