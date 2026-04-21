from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd


REGION_KEYS = ["sido", "sigungu", "eupmyeondong"]


@dataclass
class RuleScorer:
    """config/feature_weights.yaml 기반 유형별 가중합 스코어러.

    weights: {category_code: {feature_name: weight, ...}, ...}
    feature_name 에 `_inverse` 서픽스가 붙은 경우, 원본 feature 값을 1-x 로 사용한다.
    (예: franchise_ratio_inverse → franchise_ratio 컬럼을 (1-x) 로 사용)
    """

    weights: Mapping[str, Mapping[str, float]]

    def score(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """positive + negative 가중치 지원.

        acc = Σ (weight_f · feature_f)
        각 feature_f ∈ [0,1] 이므로
            min_possible = Σ min(w,0),   max_possible = Σ max(w,0)
        normalized = (acc − min_possible) / (max_possible − min_possible) → [0,1]
        """
        out = features_df[REGION_KEYS].copy()
        for category, feature_weights in self.weights.items():
            acc = np.zeros(len(features_df), dtype=float)
            for feature, weight in feature_weights.items():
                values = self._resolve_feature(features_df, feature)
                acc += values * float(weight)
            min_p = sum(min(float(w), 0.0) for w in feature_weights.values())
            max_p = sum(max(float(w), 0.0) for w in feature_weights.values())
            span = max_p - min_p
            if span <= 0:
                out[category] = 0.0
            else:
                out[category] = ((acc - min_p) / span).clip(0.0, 1.0)
        return out

    @staticmethod
    def _resolve_feature(df: pd.DataFrame, feature: str) -> np.ndarray:
        if feature in df.columns:
            return df[feature].fillna(0.0).to_numpy(dtype=float)
        if feature.endswith("_inverse"):
            base = feature[: -len("_inverse")]
            if base in df.columns:
                return (1.0 - df[base].fillna(0.0)).to_numpy(dtype=float)
        return np.zeros(len(df), dtype=float)
