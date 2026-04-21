"""Hill climbing 가중치 최적화 — RuleScorer 직접 사용."""
from __future__ import annotations

import copy
import random
from pathlib import Path

import pandas as pd
import yaml

from src.evaluation.evaluator import evaluate
from src.scoring import RuleScorer
from src.scoring.rule_scorer import REGION_KEYS
from src.evaluation.ground_truth import GROUND_TRUTH


def _count_hits(weights: dict, feat: pd.DataFrame) -> int:
    scorer = RuleScorer(weights=weights)
    scores = scorer.score(feat)
    cats = [c for c in scores.columns if c not in REGION_KEYS]
    hits = 0
    for expected, dongs in GROUND_TRUTH.items():
        for s, g, d in dongs:
            m = scores[(scores.sido == s) & (scores.sigungu == g) &
                       (scores.eupmyeondong == d)]
            if not len(m):
                continue
            r = m.iloc[0]
            top = max(cats, key=lambda c: r[c])
            if top == expected:
                hits += 1
    return hits


def hill_climb(
    initial_weights: dict,
    feat: pd.DataFrame,
    n_iters: int = 2000,
    step_size: float = 0.05,
    seed: int = 42,
    weight_clip: float = 0.5,        # weight 절대값 상한
) -> tuple[dict, int]:
    rnd = random.Random(seed)
    current = copy.deepcopy(initial_weights)
    current_hits = _count_hits(current, feat)
    best = current
    best_hits = current_hits
    print(f"[hill-climb] init: {best_hits}/73")

    cats = list(current.keys())
    for it in range(n_iters):
        cand = copy.deepcopy(current)
        cat = rnd.choice(cats)
        features = list(cand[cat].keys())
        feature = rnd.choice(features)
        delta = rnd.uniform(-step_size, step_size)
        new_val = cand[cat][feature] + delta
        # ±weight_clip 로 제한
        new_val = max(-weight_clip, min(weight_clip, new_val))
        cand[cat][feature] = round(new_val, 3)

        cand_hits = _count_hits(cand, feat)
        if cand_hits >= current_hits:  # ≥ to allow lateral moves
            if cand_hits > current_hits:
                current = cand
                current_hits = cand_hits
                if cand_hits > best_hits:
                    best = cand
                    best_hits = cand_hits
                    print(f"[hill-climb] iter {it}: {best_hits}/73 "
                          f"(cat={cat} feat={feature} Δ={delta:+.3f})")
            else:
                # lateral: accept with prob 0.3
                if rnd.random() < 0.3:
                    current = cand

    return best, best_hits


def climb_with_random_restarts(
    initial_weights: dict,
    feat: pd.DataFrame,
    n_restarts: int = 5,
    n_iters: int = 1500,
) -> tuple[dict, int]:
    best, best_hits = hill_climb(initial_weights, feat, n_iters=n_iters, seed=1)
    print(f"[restart 1] best {best_hits}/73")
    for r in range(2, n_restarts + 1):
        candidate, hits = hill_climb(best, feat, n_iters=n_iters, seed=r * 7)
        print(f"[restart {r}] {hits}/73")
        if hits > best_hits:
            best = candidate
            best_hits = hits
    return best, best_hits
