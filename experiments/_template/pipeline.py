from __future__ import annotations

from pathlib import Path
from typing import Any


def run_experiment(context: dict[str, Any]) -> dict[str, Any]:
    """Train, validate and test one experiment, then return standardized metrics."""
    dataset_path = Path(context["dataset_path"])
    if not dataset_path.is_file():
        raise FileNotFoundError(f"전처리 데이터를 찾을 수 없습니다: {dataset_path}")

    # 여기에 모델 학습 코드를 작성합니다.
    # 반드시 참여자 단위 Train/Validation/Test 분리와 Validation-only 임계값 선택을 적용합니다.
    raise NotImplementedError("템플릿을 복사한 뒤 실험 코드를 구현하세요.")

    # 반환 예시(숫자를 직접 적지 말고 실제 평가 결과를 반환):
    # return {
    #     "metrics": {
    #         "recall": recall,
    #         "specificity": specificity,
    #         "auroc": auroc,
    #         "auprc": auprc,
    #         "f1": f1,
    #         "brier": brier,
    #     },
    #     "artifact": "model.joblib",
    #     "notes": "실험 결론",
    # }
