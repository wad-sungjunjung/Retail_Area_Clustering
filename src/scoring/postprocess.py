"""분류 후처리 규칙.

각 유형별 absolute threshold 적용. 미달 시 rank1 강등:
 - rank2 가 valid (not None) 이면: r2→r1, r3→r2, 원래 r1→r3
 - rank2 가 None 이면: rank1 = GENERAL (empty 방지)
"""
from __future__ import annotations

import pandas as pd


def _force_promote(df: pd.DataFrame, mask, target_category: str,
                   only_from_general: bool = True) -> int:
    """mask 인 행의 rank1 을 target_category 로 강제.

    only_from_general=True (기본): rank1 이 GENERAL 인 경우만 force.
    이미 다른 유형으로 분류된 동은 건드리지 않음.
    """
    affected = 0
    for idx in df[mask].index:
        cur = df.at[idx, "rank1_category"]
        if cur == target_category:
            continue
        if only_from_general and cur != "GENERAL":
            continue
        sc = df.at[idx, "all_scores"]
        score = float(sc.get(target_category, 0.5)) if isinstance(sc, dict) else 0.5
        df.at[idx, "rank1_category"] = target_category
        df.at[idx, "rank1_score"] = round(score, 4)
        df.at[idx, "rank2_category"] = None
        df.at[idx, "rank2_score"] = None
        df.at[idx, "rank3_category"] = None
        df.at[idx, "rank3_score"] = None
        affected += 1
    return affected


def apply_premium_force(df: pd.DataFrame, features_df: pd.DataFrame,
                        min_premium_ratio: float = 0.12,
                        min_foreign_ratio: float = 0.15) -> pd.DataFrame:
    """PREMIUM 확실 조건: prem_ratio >= 0.12 AND foreign_ratio >= 0.15"""
    merged = df.merge(
        features_df[["sido", "sigungu", "eupmyeondong",
                     "premium_industry_ratio", "foreign_restaurant_ratio"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged[["premium_industry_ratio", "foreign_restaurant_ratio"]] = \
        merged[["premium_industry_ratio", "foreign_restaurant_ratio"]].fillna(0)
    mask = ((merged["premium_industry_ratio"] >= min_premium_ratio) &
            (merged["foreign_restaurant_ratio"] >= min_foreign_ratio))
    n = _force_promote(merged, mask, "PREMIUM")
    print(f"[force] PREMIUM: {n} promoted "
          f"(prem>={min_premium_ratio} AND foreign>={min_foreign_ratio})")
    return merged.drop(columns=["premium_industry_ratio", "foreign_restaurant_ratio"])


def apply_tourist_force(df: pd.DataFrame, poi_df: pd.DataFrame,
                        min_at4_share: float = 0.55,
                        min_ad5_share: float = 0.70) -> pd.DataFrame:
    """TOURIST 확실 조건: 관광지·숙박 POI 비중 둘 다 상위 (rank)."""
    merged = df.merge(poi_df[["sido", "sigungu", "eupmyeondong"]],
                      on=["sido", "sigungu", "eupmyeondong"], how="left")
    feat_path = "data/processed/area_features.parquet"
    import pandas as _pd
    feat = _pd.read_parquet(feat_path)
    merged = merged.merge(
        feat[["sido", "sigungu", "eupmyeondong",
              "tourist_spot_share", "accommodation_share"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged[["tourist_spot_share", "accommodation_share"]] = \
        merged[["tourist_spot_share", "accommodation_share"]].fillna(0)
    mask = ((merged["tourist_spot_share"] >= min_at4_share) &
            (merged["accommodation_share"] >= min_ad5_share))
    n = _force_promote(merged, mask, "TOURIST_DINING")
    print(f"[force] TOURIST: {n} promoted "
          f"(tourist>={min_at4_share} AND accom>={min_ad5_share})")
    return merged.drop(columns=["tourist_spot_share", "accommodation_share"])


def apply_nightlife_force(df: pd.DataFrame, features_df: pd.DataFrame,
                          min_club_rank: float = 0.95,
                          min_alcohol_ratio: float = 0.10) -> pd.DataFrame:
    """NIGHTLIFE 확실 조건: 클럽 POI rank 상위 + 주점 비중."""
    merged = df.merge(
        features_df[["sido", "sigungu", "eupmyeondong",
                     "club_count_rank", "alcohol_industry_ratio"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged[["club_count_rank", "alcohol_industry_ratio"]] = \
        merged[["club_count_rank", "alcohol_industry_ratio"]].fillna(0)
    mask = ((merged["club_count_rank"] >= min_club_rank) &
            (merged["alcohol_industry_ratio"] >= min_alcohol_ratio))
    n = _force_promote(merged, mask, "NIGHTLIFE_DINING")
    print(f"[force] NIGHTLIFE: {n} promoted "
          f"(club>={min_club_rank} AND alcohol>={min_alcohol_ratio})")
    return merged.drop(columns=["club_count_rank", "alcohol_industry_ratio"])


def apply_family_force(df: pd.DataFrame, features_df: pd.DataFrame,
                       min_apt_rank: float = 0.90,
                       min_academy_share: float = 0.50) -> pd.DataFrame:
    """FAMILY 확실 조건: 아파트 수 상위 + 학원 POI 비중."""
    merged = df.merge(
        features_df[["sido", "sigungu", "eupmyeondong",
                     "apartment_count_rank", "academy_share"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged[["apartment_count_rank", "academy_share"]] = \
        merged[["apartment_count_rank", "academy_share"]].fillna(0)
    mask = ((merged["apartment_count_rank"] >= min_apt_rank) &
            (merged["academy_share"] >= min_academy_share))
    n = _force_promote(merged, mask, "FAMILY_RESIDENTIAL")
    print(f"[force] FAMILY: {n} promoted "
          f"(apt>={min_apt_rank} AND academy>={min_academy_share})")
    return merged.drop(columns=["apartment_count_rank", "academy_share"])


def apply_office_force(df: pd.DataFrame, features_df: pd.DataFrame,
                       min_bank_share: float = 0.90,
                       min_subway_share: float = 0.80,
                       min_business_density: float = 0.90) -> pd.DataFrame:
    """OFFICE 확실 조건: 은행·지하철·업무밀도 모두 상위."""
    merged = df.merge(
        features_df[["sido", "sigungu", "eupmyeondong",
                     "bank_share", "subway_station_share", "business_density"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    cols = ["bank_share", "subway_station_share", "business_density"]
    merged[cols] = merged[cols].fillna(0)
    mask = ((merged["bank_share"] >= min_bank_share) &
            (merged["subway_station_share"] >= min_subway_share) &
            (merged["business_density"] >= min_business_density))
    n = _force_promote(merged, mask, "OFFICE_LUNCH")
    print(f"[force] OFFICE: {n} promoted "
          f"(bank>={min_bank_share} AND subway>={min_subway_share} "
          f"AND biz>={min_business_density})")
    return merged.drop(columns=cols)


def promote_campus_if_univ(
    df: pd.DataFrame,
    univ_2km: pd.DataFrame,
    min_universities: int = 2,
) -> pd.DataFrame:
    """rank1이 GENERAL인데 2km 내 대학 수 >= min 이면 CAMPUS 로 승격.

    실제 대학가이지만 주거·상업 혼재로 rule_score 낮아 GENERAL 배정된 경우 복구.
    """
    merged = df.merge(
        univ_2km[["sido", "sigungu", "eupmyeondong", "kakao_univ_sc4_2km"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged["kakao_univ_sc4_2km"] = merged["kakao_univ_sc4_2km"].fillna(0)
    mask = ((merged["rank1_category"] == "GENERAL") &
            (merged["kakao_univ_sc4_2km"] >= min_universities))
    n = int(mask.sum())
    if n:
        for idx in merged[mask].index:
            sc = merged.at[idx, "all_scores"]
            campus_score = sc.get("CAMPUS_CASUAL", 0.0) if isinstance(sc, dict) else 0.0
            merged.at[idx, "rank1_category"] = "CAMPUS_CASUAL"
            merged.at[idx, "rank1_score"] = round(float(campus_score), 4)
            merged.at[idx, "rank2_category"] = None
            merged.at[idx, "rank2_score"] = None
            merged.at[idx, "rank3_category"] = None
            merged.at[idx, "rank3_score"] = None
    print(f"[postprocess] GENERAL→CAMPUS promoted (univ>={min_universities}): {n}")
    return merged.drop(columns=["kakao_univ_sc4_2km"])


def enforce_threshold(df: pd.DataFrame, threshold_primary: float = 0.6) -> pd.DataFrame:
    """postprocess 체인 종료 후 rank1_score < threshold → GENERAL 로 일괄 전환.

    이중 demote 결과 rank1 score 가 rank2/3 보다 낮아지는 경우도 커버.
    """
    n_before = int((df["rank1_category"] == "GENERAL").sum())
    mask = (df["rank1_category"] != "GENERAL") & (
        df["rank1_score"].astype(float) < threshold_primary
    )
    n_new = int(mask.sum())
    if n_new:
        df.loc[mask, "rank1_category"] = "GENERAL"
        df.loc[mask, "rank1_score"] = 1.0 - df.loc[mask, "rank1_score"].astype(float)
        for col in ["rank2_category", "rank2_score", "rank3_category", "rank3_score"]:
            df.loc[mask, col] = None
    print(f"[postprocess] threshold enforcement: {n_new} dongs → GENERAL "
          f"(total GENERAL: {n_before + n_new})")

    # rank2/3 이 rank1_score 보다 높으면 해당 rank 제거 (demote 잔재)
    for n in (2, 3):
        col_c = f"rank{n}_category"
        col_s = f"rank{n}_score"
        bad = (df[col_s].notna() & df["rank1_score"].notna() &
               (df[col_s].astype(float) > df["rank1_score"].astype(float)))
        if bad.sum():
            df.loc[bad, col_c] = None
            df.loc[bad, col_s] = None

    return df


def _demote_rank1(df: pd.DataFrame, idx) -> None:
    """rank1 을 강등. rank2 가 None 이면 GENERAL 로 변환."""
    r1c = df.at[idx, "rank1_category"]
    r1s = df.at[idx, "rank1_score"]
    r2c = df.at[idx, "rank2_category"]
    r2s = df.at[idx, "rank2_score"]
    r3c = df.at[idx, "rank3_category"]
    r3s = df.at[idx, "rank3_score"]
    is_none = r2c is None or (isinstance(r2c, float) and pd.isna(r2c))
    if is_none:
        df.at[idx, "rank1_category"] = "GENERAL"
        df.at[idx, "rank1_score"] = 1.0 - float(r1s) if r1s is not None else 0.5
        df.at[idx, "rank2_category"] = None
        df.at[idx, "rank2_score"] = None
        df.at[idx, "rank3_category"] = None
        df.at[idx, "rank3_score"] = None
        return
    df.at[idx, "rank1_category"] = r2c
    df.at[idx, "rank1_score"] = r2s
    df.at[idx, "rank2_category"] = r3c
    df.at[idx, "rank2_score"] = r3s
    df.at[idx, "rank3_category"] = r1c
    df.at[idx, "rank3_score"] = r1s


def apply_campus_threshold(
    classification_df: pd.DataFrame,
    univ_sc4_1km: pd.DataFrame,
    min_universities_1km: int = 2,
    univ_sc4_3km: pd.DataFrame | None = None,
    min_universities_3km: int = 3,
    count_col: str = "kakao_univ_sc4_1km",
) -> pd.DataFrame:
    """CAMPUS 유지 조건: (1km 내 >= min_1km) OR (3km 내 >= min_3km).
    둘 다 실패하면 rank2로 강등 (rank2→rank1, rank3→rank2, CAMPUS→rank3).

    1km 엄격 + 3km 보조 → 캠퍼스 중심이 1km 밖인 지방 대학가도 실 대학가 보호.
    """
    merged = classification_df.merge(
        univ_sc4_1km[["sido", "sigungu", "eupmyeondong", count_col]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged[count_col] = merged[count_col].fillna(0)
    primary_col = count_col
    if univ_sc4_3km is not None:
        merged = merged.merge(
            univ_sc4_3km[["sido", "sigungu", "eupmyeondong", "kakao_univ_sc4"]],
            on=["sido", "sigungu", "eupmyeondong"], how="left",
        )
        merged["kakao_univ_sc4"] = merged["kakao_univ_sc4"].fillna(0)
        fails_campus = ((merged[primary_col] < min_universities_1km) &
                        (merged["kakao_univ_sc4"] < min_universities_3km))
    else:
        fails_campus = merged[primary_col] < min_universities_1km

    mask = (merged["rank1_category"] == "CAMPUS_CASUAL") & fails_campus
    n_affected = int(mask.sum())

    if n_affected:
        for idx in merged[mask].index:
            _demote_rank1(merged, idx)

    print(f"[postprocess] CAMPUS demoted "
          f"(1km<{min_universities_1km} AND 3km<{min_universities_3km}): {n_affected}")
    cols_drop = [c for c in [count_col, "kakao_univ_sc4"] if c in merged.columns]
    return merged.drop(columns=cols_drop)


def apply_tourist_threshold(
    classification_df: pd.DataFrame,
    poi_df: pd.DataFrame,
    min_at4: int = 3,
    min_ad5: int = 10,
) -> pd.DataFrame:
    """rank1 == TOURIST_DINING 인데 관광명소(AT4) 또는 숙박(AD5) POI 수 기준 미달시 강등.
    조건: kakao_AT4_count >= min_at4 AND kakao_AD5_count >= min_ad5
    """
    merged = classification_df.merge(
        poi_df[["sido", "sigungu", "eupmyeondong", "kakao_AT4_count", "kakao_AD5_count"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged["kakao_AT4_count"] = merged["kakao_AT4_count"].fillna(0)
    merged["kakao_AD5_count"] = merged["kakao_AD5_count"].fillna(0)

    mask = ((merged["rank1_category"] == "TOURIST_DINING") &
            ((merged["kakao_AT4_count"] < min_at4) |
             (merged["kakao_AD5_count"] < min_ad5)))
    n_affected = int(mask.sum())

    if n_affected:
        for idx in merged[mask].index:
            _demote_rank1(merged, idx)

    print(f"[postprocess] TOURIST demoted "
          f"(AT4<{min_at4} OR AD5<{min_ad5}): {n_affected}")
    return merged.drop(columns=["kakao_AT4_count", "kakao_AD5_count"])


def apply_premium_threshold(
    classification_df: pd.DataFrame,
    features_df: pd.DataFrame,
    min_premium_ratio: float = 0.12,
    min_foreign_ratio: float = 0.15,
) -> pd.DataFrame:
    """rank1 == PREMIUM 인데 고급업종·외국음식 비율 기준 미달 시 강등."""
    merged = classification_df.merge(
        features_df[["sido", "sigungu", "eupmyeondong",
                     "premium_industry_ratio", "foreign_restaurant_ratio"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    merged[["premium_industry_ratio", "foreign_restaurant_ratio"]] = \
        merged[["premium_industry_ratio", "foreign_restaurant_ratio"]].fillna(0)

    mask = ((merged["rank1_category"] == "PREMIUM") &
            ((merged["premium_industry_ratio"] < min_premium_ratio) |
             (merged["foreign_restaurant_ratio"] < min_foreign_ratio)))
    n_affected = int(mask.sum())

    if n_affected:
        for idx in merged[mask].index:
            _demote_rank1(merged, idx)

    print(f"[postprocess] PREMIUM demoted "
          f"(prem<{min_premium_ratio} OR foreign<{min_foreign_ratio}): {n_affected}")
    return merged.drop(columns=["premium_industry_ratio", "foreign_restaurant_ratio"])
