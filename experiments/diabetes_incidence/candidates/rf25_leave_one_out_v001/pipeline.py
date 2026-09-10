"""개별 실험에서 구현할 누수 방지 학습 파이프라인."""

from __future__ import annotations

from typing import Any


def run_experiment(context: dict[str, Any]) -> dict[str, Any]:
    """참여자 단위 분할과 누수 방지 학습을 구현한다.

    Fit preprocessing on train only, select the threshold on validation only,
    evaluate test once, and return recall together with specificity.

    반환 형식은 다음과 같다.
    {
      "metrics": {
        "recall": ..., "specificity": ..., "auroc": ..., "auprc": ...,
        "f1": ..., "brier_score": ..., "threshold": ...,
        "confusion_matrix": {"true_positive": ..., "false_positive": ...,
                             "true_negative": ..., "false_negative": ...}
      },
      "artifact": "model.joblib"
    }
    """
    from src.ml.evaluation.rf25_leave_one_out import run

    return run(context)
