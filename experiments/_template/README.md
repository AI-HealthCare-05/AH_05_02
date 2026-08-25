# 새 실험 템플릿

직접 복사하는 대신 아래 명령으로 표준 폴더를 생성합니다.

```powershell
.\scripts\ml-experiment.ps1 new rf_25features_v001 -Kind candidate -Owner "양준혁"
```

1. 생성된 `experiment.json`에서 데이터·특성 스키마를 확인합니다.
2. `pipeline.py`의 `run_experiment(context)`를 구현합니다.
3. `uv run python -m src.ml.experiments.runner validate`로 검사합니다.
4. `uv run python -m src.ml.experiments.runner run <experiment_id>`로 실행합니다.

원본 데이터, 전처리 CSV, 모델 바이너리는 커밋하지 않습니다.
