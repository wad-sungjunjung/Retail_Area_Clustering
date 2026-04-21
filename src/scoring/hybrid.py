from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .rule_scorer import REGION_KEYS

GENERAL_CODE = "GENERAL"


@dataclass
class HybridClassifier:
    alpha: float = 0.6
    threshold_primary: float = 0.4
    threshold_secondary: float = 0.4
    top_k: int = 3
    min_margin: float = 0.0              # rank1 - rank2 < min_margin → GENERAL

    def classify(
        self,
        rule_scores: pd.DataFrame,
        ml_probs: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        category_cols = [c for c in rule_scores.columns if c not in REGION_KEYS]

        if ml_probs is not None:
            merged = rule_scores.merge(
                ml_probs, on=REGION_KEYS, suffixes=("_rule", "_ml")
            )
            final = rule_scores[REGION_KEYS].copy()
            for cat in category_cols:
                final[cat] = (
                    self.alpha * merged[f"{cat}_rule"]
                    + (1.0 - self.alpha) * merged[f"{cat}_ml"]
                )
        else:
            final = rule_scores.copy()

        rows = []
        for _, row in final.iterrows():
            scores = {cat: float(row[cat]) for cat in category_cols}
            sorted_items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

            top_category, top_score = sorted_items[0]
            second_score = sorted_items[1][1] if len(sorted_items) > 1 else 0.0
            margin = top_score - second_score
            if top_score < self.threshold_primary or margin < self.min_margin:
                primary = GENERAL_CODE
                primary_score = 1.0 - top_score
                secondary = []
            else:
                primary = top_category
                primary_score = top_score
                secondary = [
                    (c, s) for c, s in sorted_items[1:]
                    if s >= self.threshold_secondary
                ]

            top_k = [(primary, primary_score)] + secondary[: self.top_k - 1]
            while len(top_k) < self.top_k:
                top_k.append((None, None))

            out = {k: row[k] for k in REGION_KEYS}
            for idx, (cat, score) in enumerate(top_k, start=1):
                out[f"rank{idx}_category"] = cat
                out[f"rank{idx}_score"] = (
                    round(score, 4) if score is not None else None
                )
            out["is_general"] = primary == GENERAL_CODE
            out["all_scores"] = {c: round(s, 4) for c, s in scores.items()}
            rows.append(out)

        return pd.DataFrame(rows)
