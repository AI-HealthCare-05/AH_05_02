# 오늘이·내일이 SHAP 3요인 계약

2026-09-14, PR #55 후속 수정. 오늘이는 shared8-waist 앙상블, 내일이는 RF25 v1이다.

## 설명 계산

- 오늘이: `exact_grouped_shap_missing_reference_v1`. 모든 입력 그룹 조합을 배치 예측하여 정확한 Shapley 값을 계산한다. 허리둘레 추정, fitted 전처리, Logistic/RF, 각 Platt 보정 및 0.7/0.3 가중합 전체가 설명 대상이다. 키·체중·BMI는 종속 관계를 보존하도록 `body_measurements` 하나로 묶는다. 오늘이 입력에 없는 운동 항목은 설명에 넣지 않는다.
- 오늘이 기준점수는 **모든 그룹을 결측으로 두고 Train-fitted 정책을 적용한 점수**다. 모집단 평균이나 비슷한 사용자 평균이 아니다. 결측 기준에 따른 민감도가 있으므로 인구집단 배경표본 기반 SHAP과 구분하고 운영 승인 전에 기준 타당성을 검토한다. 기존 한 변수 결측 차이와 달리 모든 조합의 한계 기여를 Shapley 가중치로 합산한다.
- 내일이: `treeshap_tree_path_dependent_v1`, SHAP 0.52.0. fitted RF 학습 경로 빈도를 기준으로 positive class 1을 설명한다. one-hot 및 결측 indicator 기여를 원 변수로 합산한다.
- 두 방식 모두 기준점수 + 전체 기여값 = 실제 모델 점수를 절대오차 1e-8 이내 검증한다. 응답은 12자리로 반올림한다. 선택한 세 요인만으로 전체 점수가 재구성되지 않으므로 `other_contribution`을 별도 반환한다.

## 카드 선택과 문구

| 모델 결과 | 우선 표시 | 다음 표시 |
|---|---|---|
| 오늘이 `screening_signal_detected=false` | 긍정 2개 | 주의 1개 |
| 오늘이 `screening_signal_detected=true` | 주의 2개 | 긍정 1개 |
| 내일이 `low` | 긍정 2개 | 주의 1개 |
| 내일이 `caution` 또는 `high` | 주의 2개 | 긍정 1개 |

양의 기여는 `↑ 주의 요인 · 점수를 높인 방향`, 음의 기여는 `↓ 긍정 요인 · 점수를 낮춘 방향`으로 표시한다. 각 방향에서 절댓값 순으로 선택한다. 중간 구간인 `caution`도 주의 우선 규칙을 사용한다. 상태가 없으면 선택하지 않는다.

절댓값 1e-10 이하 및 비유한 값은 제외한다. 이 값은 수치 잡음 제거 기준이고 의료적 영향 크기 기준이 아니다. 반대 방향 요인이 부족하면 최대 3개보다 적게 표시하며, 중복 또는 임의 요인으로 채우지 않는다. `selection_status=insufficient_directional_factors`로 구분한다. 긍정 요인이 부족하다는 사실이 질병 확정을 뜻하지 않는다.

`큰·보통·작은 영향` 경계는 아직 검증·승인되지 않았으므로 현재 화면에 임의 배지를 생성하지 않는다. 향후 고정 Train/Validation 분포에서 모델별 기준을 버전화한 뒤 추가한다. Test로 기준을 선택하지 않는다.

## 연구 응답 및 공개 경계

`items`는 카드용 최대 3개, `all_items`는 관리자 검증용 전체 기여, `other_contribution`은 나머지 합계다. `model_version`, `method`, `explanation_version`, `baseline_definition`을 함께 보존한다. 예시는 `docs/api/examples/today_tomorrow_xai_research_response.json`을 참조한다.

수치 계산 검증과 운영 승인은 별개다. 계산 성공 시 `shap_claimed=true`, `additivity_verified=true`이지만 `status=research_only`, `display_allowed=false`는 유지한다. 모델 실패를 낮음으로 바꾸지 않으며, 설명만 실패하면 기존 예측은 보존하고 `explanation.status=unavailable`과 빈 요인을 반환한다.

현재 공개 risk-factors API는 승인 저장 경로가 없어 빈 목록을 반환한다. 이 변경은 관리자 연구 추론의 실제 설명 계산과 향후 승인 응답의 프론트 2+1 렌더링을 구현한다. 공개 서비스 활성화나 설명 저장 스키마 변경은 포함하지 않는다. 프론트는 모델 승인, 설명 승인, SHAP 확인, 명시적 `display_allowed=true`를 통과한 경우만 표시한다.

## 검증

`tests/ml/test_shap_explanations.py`: 알려진 상호작용의 정확한 배분, 체격 그룹 공동 마스킹, TreeSHAP one-hot/결측 합산, 가산성, 방향별 2+1, 부족·중립·실패 처리.

`tests/ml/test_actual_service_candidates.py`: 해시 검증한 실제 두 Artifact에서 기존 예측점수 유지, 설명 가산성, 반복 전체 응답 일치.

`tests/frontend/ui_ux_rules.test.cjs`: 방향별 선택, 결과 미정·공개 금지 차단, 안전한 문구. `partial_analysis.test.cjs`: 부분 실패 및 재시도 회귀.

통합 Artifact·입력·성능·지연시간과 Release Gate는 `TODAY8_TOMORROW_RF25_XAI_RUNTIME_HANDOFF.md`에 최신 SHAP 기준으로 기록했다. 다만 운영 환경의 큐·Redis·DB를 포함한 종단 지연과 기준점수의 임상적 타당성은 별도 검토가 필요하다.
