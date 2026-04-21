"""GT 기반 자동 가중치 학습 (multi-class logistic regression)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.evaluation.ground_truth import GROUND_TRUTH


REGION_KEYS = ["sido", "sigungu", "eupmyeondong"]


def _build_xy(feat: pd.DataFrame, feature_cols: list[str]):
    idx_lookup = {(r.sido, r.sigungu, r.eupmyeondong): i for i, r in feat.iterrows()}
    X, y = [], []
    for cat, dongs in GROUND_TRUTH.items():
        for key in dongs:
            i = idx_lookup.get(key)
            if i is None:
                continue
            X.append(feat.loc[i, feature_cols].to_numpy(dtype=float))
            y.append(cat)
    return np.array(X), np.array(y)


def _select_feature_cols(feat: pd.DataFrame) -> list[str]:
    exclude = set(REGION_KEYS) | {"lon", "lat", "total_business"}
    return [c for c in feat.columns if c not in exclude]


def learn_weights(feat: pd.DataFrame, C: float = 1.0, l1_ratio: float = 0.5):
    cols = _select_feature_cols(feat)
    X, y = _build_xy(feat, cols)
    print(f"[autotune] X={X.shape}, y classes={sorted(set(y))}")

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    clf = LogisticRegression(
        penalty="elasticnet", solver="saga",
        C=C, l1_ratio=l1_ratio,
        max_iter=5000,
        class_weight="balanced",
    )
    clf.fit(Xs, y)

    classes = clf.classes_
    # inverse-scale coefficients back to raw feature space
    coefs_raw = clf.coef_ / scaler.scale_  # (n_class, n_feat)
    intercepts_raw = clf.intercept_ - (clf.coef_ * scaler.mean_ / scaler.scale_).sum(1)
    _ = intercepts_raw  # not stored

    weights: dict[str, dict[str, float]] = {}
    for ci, cat in enumerate(classes):
        entries = {}
        for fi, fname in enumerate(cols):
            w = float(coefs_raw[ci, fi])
            if abs(w) < 1e-3:  # drop near-zero
                continue
            entries[str(fname)] = round(w, 3)
        weights[str(cat)] = entries
    return weights, clf, scaler, cols


def save_weights(weights: dict, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(weights, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)
