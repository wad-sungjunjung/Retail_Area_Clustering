from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .rule_scorer import REGION_KEYS


@dataclass
class MlClusterer:
    """GMM 기반 보조 확률 산출기.

    각 샘플에 대해 GMM soft assignment 를 구한 뒤, 각 클러스터 중심(centroid)의
    rule 기반 카테고리 스코어를 이용해 `P(category | sample)` 를 추정한다.
    """

    n_components: int = 8
    random_state: int = 42
    method: str = "gmm"

    def fit_predict_proba(
        self,
        features_df: pd.DataFrame,
        rule_scorer,
        feature_columns: list[str],
    ) -> Optional[pd.DataFrame]:
        try:
            from sklearn.mixture import GaussianMixture
        except Exception:
            return None

        X = features_df[feature_columns].fillna(0.0).to_numpy(dtype=float)
        if len(X) <= self.n_components:
            return None

        gmm = GaussianMixture(
            n_components=self.n_components,
            covariance_type="diag",
            random_state=self.random_state,
        )
        gmm.fit(X)
        sample_cluster_proba = gmm.predict_proba(X)  # (n_samples, n_clusters)

        centroid_df = pd.DataFrame(gmm.means_, columns=feature_columns)
        centroid_df[REGION_KEYS[0]] = "_c"
        centroid_df[REGION_KEYS[1]] = "_c"
        centroid_df[REGION_KEYS[2]] = [f"c{i}" for i in range(self.n_components)]
        centroid_scores = rule_scorer.score(centroid_df)
        category_cols = [c for c in centroid_scores.columns if c not in REGION_KEYS]
        centroid_mat = centroid_scores[category_cols].to_numpy(dtype=float)

        sample_category_prob = sample_cluster_proba @ centroid_mat
        max_per_row = sample_category_prob.max(axis=1, keepdims=True)
        max_per_row = np.where(max_per_row > 0, max_per_row, 1.0)
        sample_category_prob = np.clip(sample_category_prob / max_per_row, 0.0, 1.0)

        out = features_df[REGION_KEYS].copy().reset_index(drop=True)
        for i, cat in enumerate(category_cols):
            out[cat] = sample_category_prob[:, i]
        return out
