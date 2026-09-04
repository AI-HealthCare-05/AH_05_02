# 공통 7변수 KNHANES 모델: scikit-learn 1.8.0 재현

## 범위와 결과

기존 1.9.0 Artifact를 1.8.0에서 읽지 않고 동일 파라미터의 새 estimator로 재학습했다.
모델 버전은 `knhanes-shared7-sk180-research-v1`이며 연구용·운영 미승인이다.
기존 Artifact와 운영 설정은 변경하지 않았다.

| 환경 | Validation Recall | Validation Specificity | Test Recall | Test Specificity | Test Precision | Test AUROC | Test AUPRC | Test FN/FP |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 기존 sklearn 1.9.0 | 0.942169 | 0.420213 | 0.930769 | 0.413074 | 0.062350 | 0.760247 | 0.106020 | 27/5459 |
| 재학습 sklearn 1.8.0 | 0.937349 | 0.425376 | 0.933333 | 0.419417 | 0.063151 | 0.760226 | 0.106135 | 26/5400 |

Test Brier는 기존 0.037524829, 재학습 0.037528710이다. 성능 동등성·우월성 검정을
실시한 것은 아니다. Python과 NumPy 버전도 다르므로 차이를 sklearn 단독 효과로
해석할 수 없다. Test는 반복 조회된 historical holdout이며 외부 검증이 아니다.

## 고정 조건

- 입력: age, height_cm, weight_kg, bmi, sex, current_smoker, education.
- Train 2016~2020: 26,005명/양성 1,140; Validation 2021~2022: 9,132명/415;
  Test 2023~2024: 9,691명/390. 원본 전달본의 split summary 및 데이터 SHA 검증.
- Logistic C=10, balanced, lbfgs/L2, max_iter=4000.
- RF 400 trees, min_samples_leaf=40, balanced_subsample, seed=20260831.
- 기본 모델 가중치 Logistic 0.7/RF 0.3. Train-only 대치·변환, Train 연도 그룹
  5-fold OOF Platt 보정, survey weight 처리도 기존 코드와 동일.
- Validation에서 Specificity>=0.42 중 Recall 최대화 후 임계값 고정, Test 평가.
- 기존 임계값 0.025817671580432865 → 새 임계값 0.02615995276723876.
- 임계값 버전: `shared7-sk180-validation-spec042-v1`.

## Artifact와 실행

- Artifact: `outputs/ml/knhanes_shared7_sk180_v001/run01/model.joblib` (Git 제외).
- 상세 결과: 같은 폴더 `results.json`.
- SHA-256: `6946553dd321189caa6fda207edd3f7a190b8fe1ed007b9a152958ea1cf2e86f`.
- Python 3.13.9, sklearn 1.8.0, NumPy 2.4.1, pandas 2.3.3, joblib 1.5.3,
  SciPy 1.17.0. 전달 trainer의 import에는 lightgbm 4.7.0이 필요하지만 학습에는 쓰지 않는다.

저장소 루트에서 해당 버전 환경과 검증된 팀 전달 디렉터리를 준비한 뒤 실행한다.

```bash
python -m src.ml.evaluation.reproduce_knhanes_shared7_sk180 \
  --handoff-dir /path/to/today_v061_team \
  --output-dir outputs/ml/knhanes_shared7_sk180_v001/new_run
```

합성 고정 입력(56세 여성, 162cm/68kg, 현재 비흡연, 교육 미입력)의 내부 점수는
0.047658176973160이다. 5회 반복 및 저장 후 재로딩 결과는 소수점 15자리에서 동일하다.
미입력 교육은 학습 최빈값으로 대치하며 실제 학력으로 간주하지 않는다.
이 점수는 진단·처방이나 검증된 개인 발병확률이 아닌 현재 위험 선별 연구 신호다.

## 후속 작업

RF25·앙상블과 sklearn 1.8.0 환경 통일을 위한 재학습 Artifact를 확보했다.
서비스 adapter, 오류 계약, 인증·표시 제한, PR 통합 검증은 별도 완료가 필요하다.
