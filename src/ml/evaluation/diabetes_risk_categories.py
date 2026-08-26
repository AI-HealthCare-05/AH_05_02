"""Validated-screening operating points for diabetes risk categories."""

from __future__ import annotations

from typing import Literal

RiskCategory = Literal["low", "moderate", "high"]


def categorize_risk_score(
    score: float,
    *,
    moderate_threshold: float,
    high_threshold: float,
) -> RiskCategory:
    """Map a model score to validation-derived screening tiers."""

    if not 0 <= score <= 1:
        raise ValueError("risk score must be between 0 and 1")
    if not 0 <= moderate_threshold < high_threshold <= 1:
        raise ValueError("risk category thresholds must satisfy 0 <= moderate < high <= 1")
    if score >= high_threshold:
        return "high"
    if score >= moderate_threshold:
        return "moderate"
    return "low"
