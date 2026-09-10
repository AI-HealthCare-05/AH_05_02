# rf_klosa_core_candidates_v001

- 담당자: 양준혁
- 상태: 연구용 후보, 운영 미승인
- 목적: 진단·처방이 아닌 다음 조사까지의 당뇨 의사진단 위험 선별·건강교육

## 실험 가설

현재 RF 25변수에 KLoSA 1~10차에서 반복 수집된 핵심 후보를 하나씩 누적하면
Train PID OOF Recall 0.80 작동점에서 Specificity 또는 AUPRC가 증가할 수 있다.

## 사용 데이터와 순차 입력

- 공통 코호트: `data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl`
- 원천: Git 제외 `data/interim/source_extract/klosa/20260413/str01~str09`
- 데이터 버전: `official_v1`
- 분할: PID 70/15/15, PID 사건 여부 층화, random state 42
- Train 내부 비교: PID 5-fold OOF

누적 순서:

1. A: 현재 25변수
2. B: `C106` 최근 1년 5kg 이상 체중변화 범주
3. C: 평균악력/BMI 상대악력
4. D: `C113` 규칙적 운동 지속기간
5. E: 최근 이틀 식사 횟수·아침식사·세 끼 완전성
6. F: 현재 하루 흡연량·주종별 음주빈도 부담·아침음주

## 제외 변수와 제외 이유

- t1와 미래 차수 변수, 당뇨 진단·치료·진단시기: 정답·미래정보 누수
- 건강검진 수검과 의료이용: 실제 위험보다 의사진단 기회를 학습할 위험
- PID·HHID: 식별자 및 반복관측 누수
- 허리둘레·혈압·혈당·HbA1c·당뇨 가족력: KLoSA에 측정값 없음

범주 코드의 응답거부·모름은 결측으로 유지한다. 비흡연자의 현재 흡연량과
비음주자의 음주부담은 구조적 0으로 처리한다. 전처리 대치와 One-Hot 범주는 각
Train fold에서만 학습한다.

## 모델과 선택 방법

- Random Forest: 500 trees, depth 8, leaf 20, `max_features=sqrt`, 무가중
- A~F 선택: Train PID OOF Recall 0.80 이상 중 Specificity, AUPRC, AUROC,
  최저 fold Recall, 적은 변수 수 순
- Validation: 모든 변형을 참고 보고하되 선택에는 사용하지 않음
- Test: OOF 선택 변형의 Validation 임계값을 확정한 후 한 번만 평가

## 평가 결과

- 실행 ID: `20260827T023642491967Z`
- 상태: `constraint_passed`
- 상세 결과: Git 제외
  `outputs/ml/rf_klosa_core_candidates_v001/20260827T023642491967Z/core_candidate_results.json`
- 선택: Train PID OOF 기준 `B_plus_weight_change_26`

### Train PID 5-fold OOF 순차 비교

| 단계 | 변수 수 | Recall | Specificity | AUROC | AUPRC | 최저 fold Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 현재 모델 | 25 | 0.8000 | 0.3614 | 0.6307 | 0.0405 | 0.7527 |
| B + 체중변화 | 26 | 0.8000 | **0.3653** | 0.6311 | 0.0403 | 0.7363 |
| C + 상대악력 | 27 | 0.8000 | 0.3470 | 0.6305 | 0.0409 | 0.7418 |
| D + 운동 지속기간 | 28 | 0.8000 | 0.3384 | 0.6306 | 0.0404 | 0.7473 |
| E + 식사 규칙성 | 31 | 0.8000 | 0.3490 | **0.6333** | 0.0406 | **0.7582** |
| F + 흡연·음주 부담 | 34 | 0.8000 | 0.3407 | 0.6305 | 0.0409 | 0.7527 |

B는 A보다 OOF Specificity가 0.0039 높아 사전 선택 규칙으로 선택됐다. 다만 AUPRC와
최저 fold Recall은 개선되지 않았으므로 효과 크기는 작고 불안정하다.

### Validation 참고 보고

Validation은 변형 선택에 사용하지 않고 각 변형의 Recall 0.80 작동점을 참고 보고했다.

| 단계 | Recall | Specificity | AUROC | AUPRC | 임계값 |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 0.8000 | 0.4941 | 0.6775 | 0.0572 | 0.02241084 |
| B | 0.8000 | 0.4938 | **0.6809** | **0.0580** | 0.02230932 |
| C | 0.8000 | 0.4954 | 0.6758 | 0.0538 | 0.02233188 |
| D | 0.8000 | 0.4806 | 0.6708 | 0.0555 | 0.02203395 |
| E | 0.8000 | 0.4869 | 0.6724 | 0.0539 | 0.02212320 |
| F | 0.8000 | 0.5082 | 0.6724 | 0.0514 | 0.02270339 |

### OOF 선택 B의 최종 Test

- Recall 0.8103
- Specificity 0.4687
- AUROC 0.6592
- AUPRC 0.0498
- F1 0.0710
- Brier Score 0.023887
- 혼동행렬: TP 158, FN 37, TN 3,613, FP 4,095

현재 표준 RF25 Test 결과인 Recall 0.8000, Specificity 0.4742, AUROC 0.6596,
AUPRC 0.0511과 비교하면 B는 Recall이 0.0103 증가했지만 Specificity가 0.0054,
AUPRC가 0.0014 감소했고 AUROC도 개선되지 않았다. 따라서 체중변화 범주는 연구상
소폭 신호가 있으나 현재 균형 1순위 모델을 교체하지 않는다. C~F 누적 추가도 Train
OOF의 Recall 0.80 기준 Specificity를 높이지 못했다.

### B 모델 Validation 임계값 민감도

각 목표 Recall 단계에서 Validation Recall 조건을 충족하면서 Specificity가 가장 높은
임계값을 선택하고, 같은 임계값을 Test에 그대로 적용했다. Test 결과는 작동점의 민감도
분석이며 임계값을 다시 고르는 근거로 사용하지 않는다. 상세 결과는 Git 제외
`outputs/ml/rf_klosa_core_candidates_v001/20260827T023642491967Z/b_model_threshold_sweep.json`에
기록했다.

| Validation 목표 Recall | 임계값 | Validation Recall | Validation Specificity | Test Recall | Test Specificity | TP | FN | TN | FP |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.70 | 0.02482957 | 0.7026 | 0.5945 | 0.6923 | 0.5719 | 135 | 60 | 4,408 | 3,300 |
| 0.75 | 0.02332766 | 0.7538 | 0.5364 | 0.7795 | 0.5135 | 152 | 43 | 3,958 | 3,750 |
| 0.80 | 0.02230932 | 0.8000 | 0.4938 | 0.8103 | 0.4687 | 158 | 37 | 3,613 | 4,095 |
| 0.85 | 0.01974082 | 0.8513 | 0.3846 | 0.8359 | 0.3534 | 163 | 32 | 2,724 | 4,984 |
| 0.90 | 0.01747521 | 0.9026 | 0.2768 | 0.8718 | 0.2539 | 170 | 25 | 1,957 | 5,751 |
| 0.95 | 0.01496518 | 0.9538 | 0.1752 | 0.9179 | 0.1629 | 179 | 16 | 1,256 | 6,452 |

Manifest의 최소 Specificity 0.30을 Validation 기준으로 적용하면 목표 Recall 0.85,
임계값 `0.01974082`가 Recall 우선 후보 중 가장 높은 단계다. 목표 Recall 0.90부터는
Validation Specificity가 0.30 미만이므로 제약을 충족하지 않는다. 기존 `0.02230932`는
Recall과 오탐 부담의 균형 비교용 작동점으로 유지한다.

### B 모델 Decision Curve Analysis

저장된 B 모델에 탐색용 Decision Curve Analysis(DCA)를 적용했다. 임계확률 0.5%~10%에서
`모델`, `모두 선별`, `아무도 선별하지 않음`의 net benefit를 비교했다. RF 병렬 합산의
경계값 부동소수점 차이를 막기 위해 웹 추론 계약과 동일하게 점수와 임계값을 소수점
12자리로 정규화했다.

| 데이터 | 임계값 | 모델 net benefit | 모두 선별 net benefit | 최선 기준 대비 증가 | 100명당 증가 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 0.01974082 | 0.009753 | 0.006019 | 0.003734 | 0.373 |
| Test | 0.01974082 | 0.007925 | 0.005033 | 0.002892 | 0.289 |
| Validation | 0.02230932 | 0.009258 | 0.003408 | 0.005850 | 0.585 |
| Test | 0.02230932 | 0.008169 | 0.002419 | 0.005750 | 0.575 |

두 작동점 모두 Validation과 Test에서 `모두 선별`과 `아무도 선별하지 않음`보다 높은
net benefit를 보였다. 평가 격자에서 양쪽 데이터에 공통으로 순편익이 양수인 중심 구간은
약 1.1%~5.4%였다. 다만 B 모델 점수는 확률 보정되지 않았으므로 이 구간과 net benefit는
임상적으로 검증된 효용이 아니다. DCA로 운영 임계값을 결정하려면 Train 내부 PID 교차검증
기반 확률 보정, 사전 정의된 임상 임계확률, 외부 또는 시간적 검증이 추가로 필요하다.

상세 JSON과 곡선은 Git 제외 실행 폴더의 `b_model_dca.json`, `b_model_dca.svg`에 저장했다.

```bash
PYTHONPATH=. .venv/bin/python \
  experiments/diabetes_incidence/candidates/rf_klosa_core_candidates_v001/dca.py \
  --run-dir outputs/ml/rf_klosa_core_candidates_v001/20260827T023642491967Z
```

## 재현

```bash
./scripts/ml-experiment.sh validate
./scripts/ml-experiment.sh run rf_klosa_core_candidates_v001
./scripts/ml-experiment.sh leaderboard
```

원자료와 모델 바이너리·실행 산출물은 Git에 커밋하지 않는다.

## 한계와 다음 실험

- KLoSA 라벨은 생물학적 발병일이 아니라 다음 조사까지 새로 보고된 당뇨 또는
  고혈당 의사진단이다.
- 식사 항목은 최근 이틀만 반영하며 장기 식습관을 대표하지 않을 수 있다.
- 상대악력은 악력계 측정이 필요하므로 웹 기본 입력으로 바로 사용할 수 없다.
- 검사·의료이용 변수를 제외해 진단기회 편향을 줄였으나 자기보고 오류는 남는다.
