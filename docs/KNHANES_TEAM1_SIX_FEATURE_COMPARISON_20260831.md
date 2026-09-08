# KNHANES 1조식 6개 입력 모델 비교

확인일: 2026-08-31  
목적: 1조 공개 방법론의 6개 입력 LR/RF 및 Platt 보정을 우리 2조의 미진단 성인 코호트와 시간 분할에서 독립 재현하여 입력 편의성과 성능을 비교한다.

## 비교 조건

- 공통 타깃: 당뇨 기진단자를 제외한 만 19세 이상 성인의 현재 당뇨 임상 위험 신호
- 공통 분할: Train 2016~2020, Validation 2021~2022, Test 2023~2024
- 공통 임계값 정책: Validation에서 Specificity 0.42 이상을 만족하며 Recall 최대화
- 6개 입력: 나이, 성별, 키, 체중, 여가 유산소 중강도 환산 분/주, 근력운동 일수/주
- 중강도 환산식: 여가 중강도 분/주 + 2 × 여가 고강도 분/주
- 1조식 전처리: complete-case, 결측 대치·clipping 없음
- 모델: LR 10개, RF 36개 후보를 Train 조사연도 OOF로 평가
- 후보 선택: 보정 후 OOF Brier 최소, 동률이면 AUPRC·AUROC
- 보정: identity와 OOF Platt를 비교하되, 요청에 따라 RF 강제 Platt 결과도 별도 보고

> 1조의 공개 최종 점수를 가져온 것이 아니다. 대상자·타깃·연도 역할을 우리 서비스 기준으로 고정한 방법론 재현 결과다. 1조 원래 프로토콜의 nested 5×4 대신 우리 모델과 동일한 조사연도 OOF를 사용했다.

## 표본

| 분할 | 기존 적격자 | 6개 complete-case | 유지율 | 양성 수 | 양성률 |
|---|---:|---:|---:|---:|---:|
| Train | 26,005 | 24,614 | 94.65% | 1,048 | 4.26% |
| Validation | 9,132 | 8,463 | 92.67% | 372 | 4.40% |
| Test | 9,691 | 8,920 | 92.04% | 343 | 3.85% |

## 같은 Test 표본 비교

| 모델 | AUROC | AUPRC | Brier↓ | Recall | Specificity | TP / FN |
|---|---:|---:|---:|---:|---:|---:|
| 6개 LR + Platt | 0.7586 | 0.1029 | **0.0360** | 0.9329 | 0.4181 | 320 / 23 |
| 6개 RF, 프로토콜 선택 | 0.7516 | 0.1012 | **0.0359** | 0.9184 | **0.4221** | 315 / 28 |
| 6개 RF + 강제 Platt | 0.7516 | 0.1012 | 0.0359 | 0.9184 | **0.4221** | 315 / 28 |
| 우리 v0.6.1, 같은 표본 | **0.7718** | **0.1091** | 0.0361 | **0.9359** | 0.4173 | **321 / 22** |

Platt는 순위 지표인 AUROC·AUPRC를 바꾸지 않는다. 선택된 RF에서는 Platt 적용 전후 분류 결과도 같았고 Brier가 아주 조금 악화되어, 1조 프로토콜의 `identity 또는 Platt` 규칙에서는 identity가 선택됐다.

## Validation 비교

| 모델 | AUROC | AUPRC | Brier↓ | Recall | Specificity | TP / FN |
|---|---:|---:|---:|---:|---:|---:|
| 6개 LR + Platt | 0.7674 | 0.1145 | 0.0406 | 0.9274 | 0.4231 | 345 / 27 |
| 6개 RF + Platt | 0.7626 | 0.1082 | 0.0405 | 0.9328 | 0.4231 | 347 / 25 |
| 우리 v0.6.1, 같은 표본 | **0.7922** | **0.1453** | **0.0399** | **0.9543** | **0.4276** | **355 / 17** |

## 해석

1. 우리 v0.6.1은 같은 Test 표본에서 6개 LR보다 양성을 1명 더 찾았으며 AUROC와 AUPRC가 높았다.
2. Test Recall 차이는 0.29%p에 불과하므로 현재 결과만으로 통계적 우월성을 주장할 수 없다.
3. 6개 LR은 입력 부담이 매우 작으면서 Recall과 Brier가 우리 모델과 거의 같아 MVP 간편 선별 모델로 경쟁력이 있다.
4. RF는 LR보다 Recall·AUROC·AUPRC가 낮았고 Platt를 강제해도 개선되지 않았다.
5. 우리 모델은 Validation에서 Recall·Specificity·AUPRC가 모두 높아 개발 단계의 일관성은 더 좋았다.
6. Test 2023~2024를 반복 확인했으므로 다음 미사용 연도 또는 외부 코호트 검증 전에는 어느 모델도 최종 운영 우승 모델로 확정하지 않는다.

## 권고안

- 기본 간편 입력: **6개 LR + Platt**를 별도 fallback 후보로 유지한다.
- 상세 입력이 확보된 경우: **우리 v0.6.1**을 enhanced 후보로 유지한다.
- 두 경로는 모델·특성·임계값 버전을 분리하고 화면에 `간편 입력` 또는 `상세 입력` 결과임을 표시한다.
- 현재 결과는 진단이나 미래 발병확률이 아니라 KNHANES 기반 현재 위험 신호 선별 보조 결과로만 표현한다.

## 공개 방법론 출처

- 1조 고정 커밋: `e76263b4765c73454f41974a2e9eb0750625d667`
- [1조 모델 실험 프로토콜](https://github.com/AI-HealthCare-05/AH_05_01/blob/e76263b4765c73454f41974a2e9eb0750625d667/tmtn_ai/contracts/model_experiment_protocol_v0_2.yaml)
- [1조 6개 입력 설정](https://github.com/AI-HealthCare-05/AH_05_01/blob/e76263b4765c73454f41974a2e9eb0750625d667/tmtn_ai/configs/model_development_v0_2.yaml)
- [1조 운동 변수 파생 코드](https://github.com/AI-HealthCare-05/AH_05_01/blob/e76263b4765c73454f41974a2e9eb0750625d667/tmtn_ai/src/activity_features.py)

## 재현

```bash
python -m src.ml.modeling.knhanes_team1_six_feature_benchmark
python -m pytest tests/ml/test_knhanes_current_screening.py -q
```

원본 의료 데이터와 개인 단위 예측값은 Git에 반입하지 않고, 집계 결과·설정·재현 코드만 공유한다.
