# rf25_pair_removal_oof_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

25개에서 2개 제외하는 300개 조합을 Train PID OOF로 전수 탐색한다.
RF25와 음주 제외 RF24를 기준선으로 함께 평가하므로 302개 비교안이다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: pid_group_70_15_15_stratified_any_event_rs42_v1
- 입력 특성 스키마: klosa_rf25_pair_removal_oof_v1

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 추가 제외 변수: 각 조합별 2개, 해당 원핫·결측지표도 제거.

## 모델과 하이퍼파라미터

튜닝 RF500, depth8, leaf39, max_samples0.7, log_loss, ccp_alpha0.00001,
bootstrap, 무가중 seed42 고정. 전처리는 각 OOF 학습부에서만 적합한다.
공통 Train PID 5-fold seed42에서 전체 평가 후 상위 5개와 두 기준선을
5-fold seed1042로 재평가한다. RF seed는 42로 유지해 분할 안정성을 비교한다.

## 임계값 결정 방법

탐색용 pooled OOF 작동점은 Spec>=0.43에서 Recall 최대화한다.
이는 최종 서비스 임계값이 아니다. seed42에서 Recall, Specificity, AUPRC로
상위 5개를 압축하고 두 시드 평균의 같은 지표 순서로 최종안을 선택한다.
각 fold 지표는 pooled OOF 임계값 기준의 기술적 분산이다.
선택안과 RF25/RF24의 최종 임계값은 Validation에서만 같은 기준으로 결정한다.
기존 RF25 고정 임계값 0.021153602801262862도 보조로 평가한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

실행: `./scripts/ml-experiment.sh run rf25_pair_removal_oof_v001`
outputs/ml/rf25_pair_removal_oof_v001 실행 폴더에 전체 OOF CSV,
results.json, selection.json과 최종 모델을 저장한다.
조합별 완료 캐시는 outputs/ml/rf25_pair_removal_oof_cache 아래
데이터·실행코드·sklearn 버전 해시별 보관하여 같은 명령 재실행 시 이어간다.
원자료·개인별 예측은 캐시 JSON에 포함하지 않는다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

300회 다중 비교, seed42 상위 후보 선택 편향, historical Test 반복 조회,
음주 제거 등 이전 탐색의 영향이 있다. OOF 탐색 점수도 독립 최종 성능이 아니다.
Test는 기준선과 OOF 선택안에만 최종 보고하며 Test로 재선택하지 않는다.
통계적 유의성·인과 효과·운영 승인 없음. CI 및 새 외부 검증은 후속 과제.
