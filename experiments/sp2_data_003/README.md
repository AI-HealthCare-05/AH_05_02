# SP2-DATA-003 축소 표본 베이스라인

## 목적

KLoSA와 KNHANES를 합치지 않고 공통 의미로 조화한 5개 변수로 모델 파이프라인의 실행 가능성을 확인합니다. 이 실험은 축소 표본 사전 검증이며 최종 모델 성능이 아닙니다.

## 입력

- KLoSA: `data/processed/official_v1/klosa_diabetes_incident_all.csv`
- KNHANES: `data/processed/official_v1/knhanes_diabetes_undiagnosed_19plus.csv`
- 설정: `configs/age_baseline.json`

원본 및 개인 단위 처리 파일은 Git에 올리지 않습니다. 실행 시 두 입력 경로를 명시적으로 전달합니다.

## 실행

```powershell
uv run --group baseline python -m src.ml.baseline.age_baseline `
  --klosa data/processed/official_v1/klosa_diabetes_incident_all.csv `
  --knhanes data/processed/official_v1/knhanes_diabetes_undiagnosed_19plus.csv `
  --output-dir experiments/sp2_data_003
```

## 출력

- `cohort_summary.csv`: 데이터셋별 타깃·포함/제외 기준과 유효 표본
- `overall_metrics.csv`: validation/test 전체 성능 및 혼동행렬
- `age_group_metrics.csv`: test 연령군별 성능 및 혼동행렬
- `sample_manifest.json`: seed, 원본 해시, 축소 표본 해시와 층별 개수

모든 출력은 집계값 또는 해시이며 개인 식별 행은 저장하지 않습니다.
