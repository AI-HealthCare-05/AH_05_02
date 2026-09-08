# 1·3조 당뇨 모델 공개자료 벤치마크 명세

확인일: 2026-08-31  
확인 범위: 각 조의 공개 GitHub 저장소에 게시된 코드·설정·집계 결과만 사용  
제외: 비공개 Notion/Drive, 원자료, 개인정보, 모델 바이너리의 재사용

## 핵심 결론

| 구분 | 1조 | 3조 |
|---|---|---|
| 공개 상태 | KNHANES 실험 프로토콜·설정 공개, 당뇨 최종 성능표는 현재 확인되지 않음 | BRFSS 2024 당뇨 학습 코드·집계 성능 공개 |
| 예측 문제 | KNHANES 현재 측정 기반 당뇨 분류 계획 | BRFSS 현재 당뇨 진단 자기보고 여부 분류 |
| 미래 발병 예측 여부 | 아님 | 아님 |
| 우리 모델과의 직접 점수 비교 | 불가 | 불가 |
| 벤치마크 가능한 부분 | nested CV, 시간 외부검증, 보정·Brier gate, 복합표본 평가 | 그룹 분할, 가중 학습·평가, 검증세트 임계값 선택, 재현 코드 |

우리 프로젝트의 KLoSA 모델은 `t0 미진단자 -> t1 약 2년 후 신규 진단`을 예측한다. 1조와 3조는 현재 상태·진단 보고 분류이므로, 공개 점수를 우리 점수보다 높거나 낮다고 해석하지 않는다. 동일한 KLoSA 타깃·분할·특성·평가 세트에 각 방법을 다시 적용한 결과만 공정한 벤치마크로 사용한다.

## 1조 공개 방법론

- 고정 커밋: `e76263b4765c73454f41974a2e9eb0750625d667`
- 데이터 역할: KNHANES 2019~2021 개발, 2022 시간 외부평가, 2023 공개된 내부 벤치마크, 2024 접근 금지
- 입력 6개: 나이, 성별, 키, 몸무게, 여가 유산소 중강도 환산 분/주, 근력운동 일수/주
- 당뇨 라벨: `diabetes_measurement_label_raw`
- 적격 조건: 라벨 존재, 6개 입력 complete case, 결측 대치·clipping 금지
- 재표집: outer 5-fold × inner 4-fold nested cross-fitting
- seed: `42`, `1042`, `2042`
- Logistic Regression: L2, `C=[0.01,0.1,1,10,100]`, `class_weight=[None,balanced]`, StandardScaler
- Random Forest: 500 trees, `max_depth=[4,8,None]`, `min_samples_leaf=[5,20,50]`, `max_features=[sqrt,1.0]`, `class_weight=[None,balanced]`
- 모델 선택: 개발 OOF calibrated Brier 우선; log loss, calibration, PR-AUC, ROC-AUC 순으로 보조 비교
- 보정: identity 또는 OOF Platt recalibration; isotonic 비활성
- 복합표본: 학습·선택은 비가중, 공개 전 `wt_itvex`, `kstrata`, `psu` 가중 민감도 분석
- CI: 층화 PSU 단위 Rao-Wu bootstrap 2,000회, seed `20260825`
- 공개 당뇨 성능: 확인되지 않음. 프로토콜만으로 성능을 추정하거나 만들어내지 않는다.

고정 링크:

- [실험 프로토콜](https://github.com/AI-HealthCare-05/AH_05_01/blob/e76263b4765c73454f41974a2e9eb0750625d667/tmtn_ai/docs/MODEL_EXPERIMENT_PROTOCOL_V0_2.md)
- [학습 설정](https://github.com/AI-HealthCare-05/AH_05_01/blob/e76263b4765c73454f41974a2e9eb0750625d667/tmtn_ai/configs/model_development_v0_2.yaml)
- [공개 브랜치](https://github.com/AI-HealthCare-05/AH_05_01/tree/e76263b4765c73454f41974a2e9eb0750625d667/tmtn_ai)

## 3조 공개 당뇨 베이스라인

- 고정 커밋: `8cb376cb6f3a9c7400db4c23eb348091b9174cd7`
- 데이터: Hugging Face `hesscl/quackrfss`, BRFSS 2024 Parquet 전체
- 예측 문제: 현재 당뇨 진단 자기보고 여부; 미래 발병 예측 아님
- 타깃: `DIABETE4=1 -> 1`, `DIABETE4 in (2,3,4) -> 0`
- 입력 9개: 연령, BMI, 성별, 교육, 소득, 고용, 운동 여부, 흡연 상태, 음주 여부
- 숫자형: 중앙값 대치 + 결측 indicator + StandardScaler
- 범주형: 최빈값 대치 + OneHotEncoder
- 분할: 미국 주(state) 단위 GroupShuffleSplit; train 33개 주, validation 9개 주, test 11개 주
- seed: `42`; 검증 분할은 `43`
- 모델: Logistic Regression, `solver=lbfgs`, `max_iter=500`
- 가중치: `_LLCPWT`를 평균 1로 정규화하여 학습·평가에 사용
- 임계값: validation에서 가중 Youden J 최대값 선택
- 시험 당뇨 결과: `n=121,915`, 가중 유병률 `0.1233`, AUROC `0.7914`, AUPRC `0.3261`, Brier `0.0949`, threshold `0.1231`, Recall `0.7580`, Specificity `0.6871`, PPV `0.2541`, NPV `0.9528`

고정 링크:

- [학습 코드](https://github.com/AI-HealthCare-05/AH_05_03/blob/8cb376cb6f3a9c7400db4c23eb348091b9174cd7/modeling/train_chronic_disease_models.py)
- [평가표](https://github.com/AI-HealthCare-05/AH_05_03/blob/8cb376cb6f3a9c7400db4c23eb348091b9174cd7/outputs/chronic_disease_model_metrics.csv)
- [모델 매니페스트](https://github.com/AI-HealthCare-05/AH_05_03/blob/8cb376cb6f3a9c7400db4c23eb348091b9174cd7/models/chronic_disease/manifest.json)
- [모델 계획 및 한계](https://github.com/AI-HealthCare-05/AH_05_03/blob/8cb376cb6f3a9c7400db4c23eb348091b9174cd7/docs/09_chronic_disease_model_plan.md)

### 3조 공개 결과 재현

```bash
git clone https://github.com/AI-HealthCare-05/AH_05_03.git
cd AH_05_03
git checkout 8cb376cb6f3a9c7400db4c23eb348091b9174cd7
uv sync
uv run python modeling/train_chronic_disease_models.py --seed 42 --max-iter 500
```

실행 시 공개 BRFSS Parquet를 내려받으므로 네트워크·디스크 사용량을 먼저 확인한다. 공개된 `.joblib`은 직접 서비스에 복사하지 않고, 고정 커밋의 코드로 다시 학습해 환경·입력·결과를 검증한다.

## 우리 프로젝트에서의 공정한 재현 규칙

1. 공통 평가 데이터는 우리 KLoSA person-period 데이터로 고정한다.
2. 타깃은 모든 방법에서 `t0 미진단 -> t1 신규 당뇨 진단`으로 동일하게 둔다.
3. 같은 PID 그룹 분할, 같은 train/validation/test, 같은 seed를 사용한다.
4. 입력은 공통 6개 또는 공통 8개처럼 동일한 feature set으로 비교한다.
5. 전처리와 보정은 train/OOF 안에서만 적합하고 test는 최종 1회 평가한다.
6. 기본 비교군은 우리 현행 모델, 1조식 LR/RF+nested CV+Platt, 3조식 weighted LR+validation Youden J로 둔다.
7. 결과는 Recall만 보지 않고 AUROC, AUPRC, Specificity, Brier, calibration, confusion matrix를 함께 기록한다.
8. 1조·3조 원점수는 참고란에만 두고 우리 KLoSA 재실행 점수와 같은 열에 순위화하지 않는다.

## 재현 결과표 양식

| 방법 | 동일 타깃 | 동일 분할 | 특성 수 | 모델/보정 | 임계값 규칙 | AUROC | AUPRC | Recall | Specificity | Brier | 비고 |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---|
| 우리 현행 후보 | 예 | 예 |  |  | 검증 OOF |  |  |  |  |  |  |
| 1조식 방법 재현 | 예 | 예 |  | LR/RF + Platt | 검증 OOF |  |  |  |  |  | 프로토콜 벤치마크 |
| 3조식 방법 재현 | 예 | 예 |  | weighted LR | validation Youden J |  |  |  |  |  | 코드 벤치마크 |

## 출처 표기 문구

> 본 벤치마크는 1조·3조가 공개 GitHub에 게시한 코드와 방법론을 참고하여, 2조의 KLoSA 미래 신규발병 타깃과 동일한 데이터 분할에서 독립적으로 재현하였다. 타 조의 원자료·개인정보·비공개 문서·모델 바이너리는 사용하지 않았다.
