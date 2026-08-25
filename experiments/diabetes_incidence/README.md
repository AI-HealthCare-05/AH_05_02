# 당뇨병 미래발병 모델 실험

| 위치 | 용도 |
| --- | --- |
| `baselines/<experiment_id>/` | Logistic Regression 등 기준 모델 |
| `candidates/<experiment_id>/` | Random Forest, XGBoost 등 단일 후보 |
| `ensembles/<experiment_id>/` | Soft Voting, Stacking 등 앙상블 |
| `leaderboard.csv` | 공통 지표로 비교한 실행 결과 |

각 실험은 `experiment.json`, `pipeline.py`, `README.md`를 한 폴더에 둡니다. 실행 결과와 모델 파일은 자동으로 `outputs/ml/`에 생성되며 Git에 올라가지 않습니다.

```powershell
uv run python -m src.ml.experiments.runner validate
uv run python -m src.ml.experiments.runner list
uv run python -m src.ml.experiments.runner run <experiment_id>
uv run python -m src.ml.experiments.runner leaderboard
```

리더보드는 Recall을 우선 정렬하되 `minimum_specificity` 통과 여부를 함께 표시합니다. 서로 다른 데이터 분할이나 특성 스키마의 결과는 직접 우열로 단정하지 않습니다.
