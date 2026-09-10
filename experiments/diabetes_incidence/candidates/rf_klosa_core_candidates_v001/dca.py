"""Run exploratory decision-curve analysis for the saved B-model bundle."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

_matplotlib_config_dir = Path(tempfile.gettempdir()) / "chronic-disease-matplotlib"
_matplotlib_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_config_dir))

import joblib  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from src.ml.evaluation.decision_curve import (  # noqa: E402
    decision_curve_rows,
    useful_threshold_ranges,
)
from src.ml.preprocessing.build_klosa_diabetes_core_candidate_cohort import (  # noqa: E402
    add_core_candidate_features,
)

from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort  # noqa: E402
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET  # noqa: E402

EXPECTED_VARIANT = "B_plus_weight_change_26"
COHORT_PATH = Path("data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl")
SOURCE_PATH = Path("data/interim/source_extract/klosa/20260413")
TARGET_THRESHOLDS = (0.01974081914501838, 0.022309322061821926)
SCORE_ROUNDING_DECIMALS = 12


def _plot(results: dict[str, Any], output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for axis, split in zip(axes, ("validation", "test"), strict=True):
        rows = results[split]["rows"]
        thresholds = [row["threshold_probability"] for row in rows]
        axis.plot(thresholds, [row["model_net_benefit"] for row in rows], label="B model", linewidth=2)
        axis.plot(thresholds, [row["screen_all_net_benefit"] for row in rows], label="Screen all", linestyle="--")
        axis.axhline(0, label="Screen none", color="black", linewidth=1)
        for threshold in TARGET_THRESHOLDS:
            axis.axvline(threshold, color="gray", linestyle=":", alpha=0.7)
        axis.set_title(split.capitalize())
        axis.set_xlabel("Threshold probability / raw RF score")
        axis.set_ylabel("Net benefit")
        axis.grid(alpha=0.2)
        axis.legend(frameon=False)
    fig.suptitle("B-model exploratory decision curve (uncalibrated)")
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def run_dca(root: Path, run_dir: Path) -> dict[str, Any]:
    """Evaluate the fixed B model on the untouched Validation and Test splits."""

    bundle = joblib.load(run_dir / "model.joblib")
    if bundle.get("selected_variant") != EXPECTED_VARIANT:
        raise ValueError(f"expected {EXPECTED_VARIANT} bundle")
    cohort = add_core_candidate_features(pd.read_pickle(root / COHORT_PATH), root / SOURCE_PATH)
    _, validation, test = split_grouped_cohort(cohort, random_state=42)
    pipeline = bundle["pipeline"]
    features = bundle["features"]
    grid = np.unique(np.concatenate((np.arange(0.005, 0.101, 0.001), np.asarray(TARGET_THRESHOLDS))))

    result: dict[str, Any] = {
        "status": "exploratory_uncalibrated_dca_not_for_clinical_decisions",
        "model_variant": EXPECTED_VARIANT,
        "feature_count": len(features),
        "split_version": bundle["split_version"],
        "feature_schema_version": bundle["feature_schema_version"],
        "threshold_range": {"minimum": 0.005, "maximum": 0.1, "grid_step": 0.001},
        "score_rounding_decimals": SCORE_ROUNDING_DECIMALS,
        "interpretation_warning": (
            "The RF scores are not probability-calibrated. Threshold probability and net benefit are exploratory "
            "and must not be interpreted as validated clinical utility."
        ),
    }
    for name, frame in (("validation", validation), ("test", test)):
        probabilities = np.round(
            pipeline.predict_proba(frame[features])[:, 1],
            SCORE_ROUNDING_DECIMALS,
        )
        rows = decision_curve_rows(
            frame[TARGET],
            probabilities,
            np.round(grid, SCORE_ROUNDING_DECIMALS),
        )
        result[name] = {
            "rows_count": len(frame),
            "events": int(frame[TARGET].sum()),
            "event_rate": float(frame[TARGET].mean()),
            "score_minimum": float(probabilities.min()),
            "score_maximum": float(probabilities.max()),
            "useful_threshold_ranges_on_grid": useful_threshold_ranges(rows),
            "rows": rows,
        }

    (run_dir / "b_model_dca.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _plot(result, run_dir / "b_model_dca.svg")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    result = run_dca(root, args.run_dir.resolve())
    summary = {
        split: {
            "events": result[split]["events"],
            "event_rate": result[split]["event_rate"],
            "useful_threshold_ranges_on_grid": result[split]["useful_threshold_ranges_on_grid"],
        }
        for split in ("validation", "test")
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
