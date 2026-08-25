# SP2 Recall 중심 당뇨 모델·앙상블 실험 보고서

## 1. 결론

- KLoSA와 KNHANES는 행 단위로 합치지 않고 각각 학습했다. 공통 변수는 `data/metadata/common_baseline_variable_mapping.csv`에서 의미·단위·코딩만 연결한다.
- KLoSA는 **t0 미진단자의 다음 인접 조사(약 2년) 신규 당뇨 진단**, KNHANES는 **현재 미진단 성인의 횡단면 당뇨 임상 기준 해당 여부**를 다룬다. 두 점수는 직접 비교하지 않는다.
- 최종 후보는 검증셋에서 `Specificity ≥ 0.50`, `AUPRC lift ≥ 1.05`를 먼저 만족한 후보 중 Recall → AUPRC → Specificity 순으로 선택했다. 테스트셋은 선택이 끝난 뒤 한 번만 평가했다.
- KLoSA 최종 후보는 Logistic Regression, KNHANES 최종 후보는 OOF 기반 Stacking이다. 둘 다 `dev/candidate`이며 검증 전 개인 발병확률로 노출하지 않는다.
- KNHANES 후보는 테스트에서 Recall 0.883이었지만 Specificity 0.492로 최소 제약을 통과하지 못했다. 성능이 좋아 보이더라도 배포 후보로 승격하지 않는다.

## 2. 실험 설계

| 항목 | 적용 내용 |
| --- | --- |
| 고정 조건 | seed `20260821`, train 6,000 / validation 2,000 / test 3,000 |
| 분할 보호 | KLoSA는 PID 그룹 교차검증, KNHANES는 층화 교차검증 |
| 전처리 | 수치형 중앙값, 범주형 최빈값·원핫인코딩을 Pipeline 내부에서 train에만 적합 |
| 누수 차단 | 혈당, HbA1c, 진단, 복약, 타깃 생성 변수를 입력에서 제외 |
| 비교 모델 | Logistic Regression, Random Forest, XGBoost, LightGBM |
| 불균형 대응 | LR/RF `class_weight`, XGBoost/LightGBM `scale_pos_weight` |
| 앙상블 | 동일 가중 Soft Voting, OOF 가중 Blending, OOF 예측 기반 Stacking |
| 임계값 | validation에서만 0.01~0.99 탐색 후 고정 |
| 보정 | OOF 확률에 sigmoid 보정 후보를 학습하고 validation에서 비교 |
| 선택 순서 | 최소 제약 통과 → Recall → AUPRC → Specificity |
| 테스트 정책 | 모델·가중치·보정·임계값 고정 후 한 번만 평가 |

## 3. 최종 후보 성능

| 데이터 | 타깃 | 검증 선택 후보 | Test AUROC | Test AUPRC | Recall | Specificity | F1 | Brier | 판정 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| KLoSA | 약 2년 후 신규 진단 | Logistic Regression | 0.605 | 0.036 | 0.613 | 0.522 | 0.061 | 0.241 | 최소 제약 통과, 낮은 절대 성능 |
| KNHANES | 현재 위험 신호 선별 | Stacking | 0.767 | 0.113 | 0.883 | 0.492 | 0.126 | 0.243 | Test Specificity 제약 미달 |

KLoSA test 양성률은 2.5%, KNHANES는 4.0%였다. AUPRC lift는 각각 1.43배와 2.82배였지만, 양성 예측률이 각각 48.1%, 52.3%라 거짓 양성 부담이 크다. Recall만 보고 운영 모델로 채택하면 안 된다.

## 4. 최종 후보의 연령군별 Test 결과

| 데이터 | 연령군 | N/양성 | Recall | Specificity | AUPRC |
| --- | --- | ---: | ---: | ---: | ---: |
| KLoSA | 19~44세 | 관측 없음 | - | - | - |
| KLoSA | 45~64세 | 1,510/30 | 0.467 | 0.774 | 0.037 |
| KLoSA | 65세 이상 | 1,490/45 | 0.711 | 0.265 | 0.039 |
| KNHANES | 19~44세 | 1,040/14 | 0.929 | 0.789 | 0.151 |
| KNHANES | 45~64세 | 1,146/52 | 0.846 | 0.379 | 0.123 |
| KNHANES | 65세 이상 | 814/54 | 0.907 | 0.254 | 0.120 |

고령층에서 높은 Recall과 함께 Specificity가 크게 하락했다. 고령층 우선 서비스라는 이유만으로 현재 후보를 적용하면 다수의 거짓 경고를 만들 수 있다.

## 5. 해석과 서비스 적용

- **KLoSA:** 19~44세 관측이 없어 해당 연령대로 일반화할 수 없다. 전체 관찰 연령을 하나의 모델로 학습하고 45~64세·65세 이상은 평가 슬라이스로 확인한다.
- **KNHANES:** 19세 이상 자료지만 횡단면이다. 19~44세에 제공할 수 있는 것은 현재 위험 신호 선별 결과이며 미래 발병 예측으로 표현하지 않는다.
- 현재 후보 출력은 내부 QA의 `risk_score_internal`과 이진 플래그로만 사용한다. `낮음/주의/높음` 범주와 개인 확률은 보정·외부검증·의료기준 합의 후 별도 버전으로 승인한다.
- 화면 문구: “입력한 현재 건강정보를 바탕으로 위험 신호를 선별한 참고 결과이며, 진단·처방이 아닙니다.”
- Redis는 성능 향상 요소가 아니다. 비동기 추론 큐, `PredictionJob` 상태, 결과 캐시에만 사용한다.

## 6. API·추적 계약

- 요청: `disease_type`, 데이터셋 모델, `model_version`, `feature_schema_version`, `threshold_version`, 정확한 feature object.
- 작업: `PredictionJob.status = pending|running|done|failed`; 성공 후에만 `prediction_id` 연결.
- 응답: 내부 점수, 모델·특성·임계값 버전, 안전 문구. RiskFactor는 검증된 설명 방법과 원변수 메타데이터가 준비되기 전 미구현으로 유지한다.
- 계약 파일: `experiments/sp2_recall_ensemble/inference_contract.json`.

## 7. 근거

- Saito와 Rehmsmeier는 불균형 자료에서 ROC만으로는 양성 예측의 거짓 양성 부담을 놓칠 수 있어 Precision-Recall 평가가 더 유익할 수 있음을 보였다. 따라서 AUPRC와 유병률 대비 lift를 함께 기록했다. https://doi.org/10.1371/journal.pone.0118432
- TRIPOD+AI는 모델 선택·튜닝 자료와 평가 자료의 분리, 판별력·보정·임상 유용성·재현성 보고를 강조한다. https://www.bmj.com/content/385/bmj-2023-078378
- PROBAST+AI는 예측모델의 편향 위험과 적용 가능성을 구조적으로 평가하도록 권고한다. https://www.bmj.com/content/388/bmj-2024-082505
- scikit-learn 공식 예제는 기본 0.5 임계값이 사용 목적에 최적이 아닐 수 있으며 교차검증으로 임계값을 선택해야 함을 설명한다. https://scikit-learn.org/stable/auto_examples/model_selection/plot_tuned_decision_threshold.html
- scikit-learn 보정 문서는 calibrator가 학습에 사용되지 않은 예측을 이용해야 함을 설명한다. https://scikit-learn.org/stable/modules/calibration.html
- XGBoost와 LightGBM 공식 문서의 `scale_pos_weight`를 사용했다. LightGBM 문서가 경고하듯 불균형 가중치는 개별 확률 추정을 나쁘게 할 수 있어 Brier와 보정 후보를 함께 확인했다. https://xgboost.readthedocs.io/en/stable/parameter.html, https://lightgbm.readthedocs.io/en/stable/Parameters.html

## 8. 다음 작업

1. 전체 표본 실행과 부트스트랩 신뢰구간을 추가한다.
2. KLoSA 신규발병 라벨의 진단 시점 불확실성과 추적 탈락 편향을 점검한다.
3. KNHANES 복합표본 가중치 기반 성능 추정을 별도로 검토한다.
4. 65세 이상에서 Recall·Specificity·보정이 동시에 유지되는지 확인한다.
5. 외부·시간 검증을 통과하기 전 모델 상태를 `candidate_internal_not_for_personal_probability_display`로 유지한다.
