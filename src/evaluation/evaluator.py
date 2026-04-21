"""GT 기반 분류 평가·진단."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

from src.evaluation.ground_truth import GROUND_TRUTH
from src.scoring import HybridClassifier, RuleScorer
from src.scoring.rule_scorer import REGION_KEYS


def evaluate(weights_path: Path, features_path: Path) -> pd.DataFrame:
    """각 GT 동에 대해 기대 카테고리가 Top1인지, 전체 스코어 반환."""
    with open(weights_path, "r", encoding="utf-8") as f:
        weights = yaml.safe_load(f)
    feat = pd.read_parquet(features_path)
    scorer = RuleScorer(weights=weights)
    scores = scorer.score(feat)
    cat_cols = [c for c in scores.columns if c not in REGION_KEYS]

    rows = []
    for expected_cat, dongs in GROUND_TRUTH.items():
        for s, g, d in dongs:
            m = scores[(scores.sido == s) & (scores.sigungu == g) &
                       (scores.eupmyeondong == d)]
            if len(m) == 0:
                continue
            r = m.iloc[0]
            sr = {c: float(r[c]) for c in cat_cols}
            ranked = sorted(sr.items(), key=lambda kv: -kv[1])
            top1 = ranked[0][0]
            top1_score = ranked[0][1]
            exp_score = sr[expected_cat]
            exp_rank = next(i for i, (c, _) in enumerate(ranked) if c == expected_cat) + 1
            rows.append({
                "expected": expected_cat,
                "region": f"{g} {d}",
                "top1": top1,
                "top1_score": round(top1_score, 3),
                "expected_score": round(exp_score, 3),
                "expected_rank": exp_rank,
                "hit": top1 == expected_cat,
                "all_scores": {c: round(v, 3) for c, v in ranked},
            })
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame) -> None:
    total = len(df)
    hit = df["hit"].sum()
    print(f"[전체] {hit}/{total} = {hit/total*100:.1f}%")
    print("\n[카테고리별]")
    for cat, grp in df.groupby("expected"):
        h = grp["hit"].sum()
        print(f"  {cat:<20s} {h}/{len(grp)}   "
              f"(avg rank={grp.expected_rank.mean():.2f})")
    print("\n[실패 case]")
    fails = df[~df.hit]
    for _, r in fails.iterrows():
        print(f"  {r.expected:<20s} | {r.region:<30s} "
              f"→ actual Top1={r.top1}({r.top1_score}) "
              f"expected={r.expected}({r.expected_score}) rank={r.expected_rank}")
