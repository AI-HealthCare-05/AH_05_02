# 실험 기록

각 실험 문서에는 데이터 버전, 전처리, 모델, 하이퍼파라미터, 시드, 평가 지표와 결론을 기록합니다.

- `sp2_data_003/`: KLoSA 미래 신규 진단과 KNHANES 현재 상태 선별의 축소 표본 베이스라인. 두 타깃의 성능은 직접 비교하지 않습니다.
- `sp2_recall_ensemble/`: LR·RF·XGBoost·LightGBM과 OOF 앙상블의 Recall 중심 축소 실험. 검증셋에서 후보·임계값을 고정하고 테스트셋은 한 번만 평가합니다.
- `sp2_tree_stacking/`: RF·XGBoost·LightGBM만 기본 모델로 사용하고 Logistic Regression으로 최종 결합한 트리 전용 Stacking 추가 실험입니다.

