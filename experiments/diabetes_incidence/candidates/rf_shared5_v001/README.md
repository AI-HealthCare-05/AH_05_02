# 공통 정보 RF 재학습

공통 7종 중 키/체중은 BMI 계산용이므로 모델 특성은 age, sex, bmi, smoking_status, education_level 5개다.
나머지 20개를 제외하고 Train 전처리·RF를 재학습한다. 기존 모델의 학습상태를 clone으로 제거하고 하이퍼파라미터만 유지한다.
수치 중앙값+결측 indicator, 범주 최빈값+onehot을 Train에서만 학습한다.
동일 PID seed42 분할, Validation Spec>=0.43에서 Recall 최대화 후 Test 평가한다.
Test는 반복 관찰된 historical holdout이며 새로운 독립 검증은 아니다.
실행: ./scripts/ml-experiment.sh run rf_shared5_v001
결과는 outputs/ml/rf_shared5_v001/<run>/comparison.json 및 model.joblib.
연구용 위험 선별 후보이며 운영 모델 교체는 수행하지 않는다.

## 실행 결과 (2026-09-09)

실행 ID: 20260909T062835867177Z. 선택 임계값 0.022121123496906234.
Validation Recall/Specificity = 0.779487/0.431039, Test = 0.769231/0.397639.
Test TP=150, FN=45, FP=4643, TN=3065. AUROC=0.627966, AUPRC=0.038715.
기존 RF25에 20개 NaN을 넣은 비교의 Test Recall .743590보다 높지만
Specificity .410872보다 낮으며, 최소 Test .40 조건을 충족하지 못했다.
Test를 본 뒤 경계를 추가 변경하지 않았다. 실행기 constraint_failed, 운영 교체 보류.
Manifest 구조 검사 40개 통과, Artifact 재로딩 후 고정 3행 확률 일치 확인.
