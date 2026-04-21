from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from src.data import load_sample_features, SAMPLE_FEATURE_COLUMNS
from src.features.sbiz_features import build_sbiz_features
from src.features.kakao_features import build_kakao_features
from src.scoring import HybridClassifier, MlClusterer, RuleScorer
from src.scoring.postprocess import (
    apply_campus_threshold, apply_tourist_threshold, apply_premium_threshold,
    enforce_threshold, promote_campus_if_univ,
    apply_premium_force, apply_tourist_force, apply_nightlife_force,
    apply_family_force, apply_office_force,
)
from src.scoring.rule_scorer import REGION_KEYS


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_weights(path: str = "config/feature_weights.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _ensure_dirs(cfg: dict) -> None:
    for key in ("data_raw", "data_interim", "data_processed"):
        Path(cfg["paths"][key]).mkdir(parents=True, exist_ok=True)


def run_collection(config_path: str) -> None:
    """Stage 1: 외부 데이터 수집.

    아직 실제 수집기는 스텁 상태. 샘플 feature store 로 대체한다.
    운영 시에는 src/collectors/* 를 활용해 data/raw 에 원천 파일을 적재한다.
    """
    cfg = load_config(config_path)
    _ensure_dirs(cfg)
    print("[collect] collectors are stubs — using bundled sample feature store.")
    df = load_sample_features()
    out = Path(cfg["paths"]["data_interim"]) / "sample_feature_source.parquet"
    df.to_parquet(out, index=False)
    print(f"[collect] wrote {len(df):,} rows → {out}")


def run_feature_build(config_path: str) -> None:
    """Stage 2: feature store 빌드.

    소상공인 상가(상권)정보 CSV 디렉토리가 존재하면 실 데이터로 동별 feature 생성.
    없으면 샘플 feature 로 대체.
    """
    cfg = load_config(config_path)
    _ensure_dirs(cfg)

    sbiz_dir = cfg["paths"].get("sbiz_csv_dir")
    if sbiz_dir and Path(sbiz_dir).is_dir():
        print(f"[features] building from sbiz CSV: {sbiz_dir}")
        df = build_sbiz_features(Path(sbiz_dir))
        print(f"[features] sbiz → {len(df):,} dongs, {len(df.columns)-3} features")
    else:
        print("[features] sbiz CSV not found — falling back to sample features.")
        df = load_sample_features()

    kakao_path = Path("data/interim/kakao_poi.parquet")
    kw_path = Path("data/interim/kakao_kw.parquet")
    kw3_path = Path("data/interim/kakao_kw3.parquet")
    univ_path = Path("data/interim/kakao_university_sc4.parquet")
    univ_2km_feat_path = Path("data/interim/kakao_university_sc4_2km.parquet")
    if kakao_path.exists():
        kfeat = build_kakao_features(
            kakao_path,
            kw_path if kw_path.exists() else None,
            kw3_path if kw3_path.exists() else None,
            univ_path if univ_path.exists() else None,
            univ_2km_feat_path if univ_2km_feat_path.exists() else None,
        )
        df = df.merge(kfeat, on=REGION_KEYS, how="left")
        for c in kfeat.columns:
            if c not in REGION_KEYS:
                df[c] = df[c].fillna(0.0)
        print(f"[features] merged kakao → {len(df.columns)-3} features")
    else:
        print("[features] kakao POI not collected yet (expected at data/interim/kakao_poi.parquet)")

    out = Path(cfg["paths"]["feature_store"])
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"[features] wrote {len(df):,} rows → {out}")


def run_classification(config_path: str) -> None:
    """Stage 3+4: Rule + ML 하이브리드 분류."""
    cfg = load_config(config_path)
    _ensure_dirs(cfg)

    weights = _load_weights()
    feature_store_path = Path(cfg["paths"]["feature_store"])
    if not feature_store_path.exists():
        run_feature_build(config_path)
    df = pd.read_parquet(feature_store_path)

    scorer = RuleScorer(weights=weights)
    rule_scores = scorer.score(df)

    ml_cfg = cfg["scoring"]["ml"]
    clusterer = MlClusterer(
        n_components=ml_cfg.get("n_components", 8),
        random_state=ml_cfg.get("random_state", 42),
        method=ml_cfg.get("method", "gmm"),
    )
    feature_cols = [c for c in df.columns if c not in REGION_KEYS]
    ml_probs: Optional[pd.DataFrame] = clusterer.fit_predict_proba(
        df, scorer, feature_cols
    )

    hybrid = HybridClassifier(
        alpha=cfg["scoring"]["alpha"],
        threshold_primary=cfg["scoring"]["threshold_primary"],
        threshold_secondary=cfg["scoring"]["threshold_secondary"],
        min_margin=cfg["scoring"].get("min_margin", 0.0),
        top_k=3,
    )
    result = hybrid.classify(rule_scores, ml_probs)

    # 후처리: CAMPUS 2km 내 < 2 이면 강등
    univ_2km_path = Path("data/interim/kakao_university_sc4_2km.parquet")
    if univ_2km_path.exists():
        u2 = pd.read_parquet(univ_2km_path)
        result = apply_campus_threshold(
            result, u2, min_universities_1km=2,
            count_col="kakao_univ_sc4_2km",
        )
    # 후처리: TOURIST AT4/AD5 POI 수 부족하면 강등
    poi_path = Path("data/interim/kakao_poi.parquet")
    if poi_path.exists():
        poi = pd.read_parquet(poi_path)
        result = apply_tourist_threshold(result, poi, min_at4=3, min_ad5=10)

    # 후처리: PREMIUM 고급업종·외국음식 비율 부족하면 강등
    result = apply_premium_threshold(
        result, df, min_premium_ratio=0.12, min_foreign_ratio=0.15,
    )

    # 최종: rank1_score < threshold_primary → GENERAL 로 일괄 전환
    result = enforce_threshold(result,
                               threshold_primary=cfg["scoring"]["threshold_primary"])

    # 유형별 force promote — 엄격한 조건 만족 시 rank1 강제 배정
    # 우선순위: PREMIUM > CAMPUS > NIGHTLIFE > TOURIST > FAMILY > OFFICE
    result = apply_premium_force(result, df)
    if univ_2km_path.exists():
        u2 = pd.read_parquet(univ_2km_path)
        result = promote_campus_if_univ(result, u2, min_universities=2)
    result = apply_nightlife_force(result, df)
    if poi_path.exists():
        result = apply_tourist_force(result, poi)
    result = apply_family_force(result, df)
    result = apply_office_force(result, df)

    out_path = Path(cfg["paths"]["classification_output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out_path, index=False)

    csv_path = out_path.with_suffix(".csv")
    display_cols = REGION_KEYS + [
        "rank1_category", "rank1_score",
        "rank2_category", "rank2_score",
        "rank3_category", "rank3_score",
        "is_general",
    ]
    result[display_cols].to_csv(csv_path, index=False)

    print(f"[classify] wrote {len(result):,} rows → {out_path}")
    print(f"[classify] wrote CSV view → {csv_path}")
    print()
    print(result[display_cols].to_string(index=False))
