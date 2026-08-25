# 간당간당 프론트엔드 API·상태·오류 처리 체크표

| 항목 | 현재 프론트 확인 내용 | API·상태 기준 | 오류·예외 처리 | 판정 | 후속 |
| --- | --- | --- | --- | --- | --- |
| 가입·동의 | 회원가입 후 로그인 토큰을 저장하고 건강정보 동의를 생성한 뒤 적합성 확인으로 이동 | `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`, `POST /api/v1/consents` | 인증 실패·동의 실패 시 공통 오류 메시지 표시 | 확인 | 실제 배포 전 약관·동의 버전 최종 확인 |
| 적합성 확인 | 연령, 당뇨병 기진단 여부, 긴급 증상을 확인하고 제외 사유별 안내를 표시 | `POST /api/v1/eligibility-checks` | `UNDER_MINIMUM_SERVICE_AGE`, `URGENT_MEDICAL_ATTENTION`, `DIAGNOSED_DIABETES`, `MODEL_AGE_OUT_OF_RANGE`, `MODEL_POPULATION_OUT_OF_SCOPE`, `CONSENT_REQUIRED`를 분리 표시 | 확인 | 백엔드 `reason_codes` 우선순위와 계속 일치 확인 |
| 건강정보 입력 | 키, 몸무게, 허리둘레, 주관적 건강상태, 식사 횟수, 혈압, 운동, 흡연, 음주를 전송 | `POST /api/v1/health-checkups` | `422` 입력 오류는 사용자에게 수정 필요 메시지 표시 | 확인 | 모델 입력 변수 8개 확정 시 화면 항목과 재대조 |
| 예측 작업 생성 | 건강정보 저장 후 비동기 예측 작업을 생성 | `POST /api/v1/prediction-jobs` | 기진단·동의 누락·모델 범위 외 사용자는 예측 작업 생성 금지 | 확인 | `prediction-jobs` 외 경로 사용 금지 유지 |
| 예측 상태 조회 | `queued/running/succeeded/failed`를 사용자 문구로 표시 | `GET /api/v1/prediction-jobs/{job_id}` | `failed + TIMEOUT`은 일반 실패와 분리해 시간초과 안내 | 확인 | 상태값 이름 변경 시 프론트 매핑 수정 |
| 예측 완료 결과 | 승인된 결과일 때만 `낮음·주의·높음` 위험 범주를 표시 | `GET /api/v1/predictions/{prediction_id}` | 승인 전·미보정·연구용 출력은 `모델 검증 중`으로 표시하고 숫자 점수 비공개 | 확인 | 승인 기준 필드명 최종 확정 필요 |
| 위험·보호요인 | 검증된 요인이 없으면 임의 요인을 만들지 않고 빈 상태 안내 | `GET /api/v1/predictions/{prediction_id}/risk-factors` | 빈 목록이면 “검증된 위험·보호요인이 제공되기 전까지 임의 요인을 표시하지 않습니다.” 표시 | 확인 | 설명 방법·출처 메타데이터 확정 후 표시 확장 |
| 고위험 안내 | 높은 위험 범주일 때 첫 번째 CTA를 의료기관 안내로 변경 | 결과 화면 내부 상태 | 챌린지보다 검사·의료기관 상담 안내 우선 | 확인 | 실제 병원 검색/검사 안내 API는 후속 |
| 챌린지 진입 | 승인 결과 또는 일반 흐름에서 일반 건강 챌린지를 선택 | `GET /api/v1/challenge-recommendations`, `POST /api/v1/challenge-cycles` | 의료기관 안내 우선 필요 시 안내 메시지 표시 | 확인 | 기진단자의 개인화 추천 차단 범위 재확인 |
| 대시보드 | 최신 위험 범주, 챌린지, 최근 7일 기록, 주간 리포트, 함께하기, 건강도구 탭 표시 | `GET /api/v1/dashboard`, `GET /api/v1/weekly-reports/current` 등 | 빈 데이터는 기록 없음·준비 중 상태로 표시 | 확인 | 탭별 빈 데이터 화면 문구 추가 점검 |

## 오늘 확인한 표시 원칙

- 서비스 이용 가능 연령은 만 19세 이상이다.
- 핵심 타깃과 현재 KLoSA 모델 적용 기준은 만 45세 이상 당뇨병 미진단자다.
- 사용자 화면에는 승인 전 개인 발병확률, 원시 모델 점수, 건강 개선율을 표시하지 않는다.
- 결과 화면은 진단·처방이 아니라 위험 선별과 건강교육 목적임을 안내한다.
- 위험·보호요인은 검증된 응답이 없으면 프론트에서 임의로 생성하지 않는다.
- 고위험 결과에서는 챌린지보다 의료기관 검사·상담 안내를 먼저 보여준다.

## 수요일 보완 우선순위

1. 실제 모델 응답의 승인 상태 필드명 확정: `result_status`, `promotion_status`, `output_status`, `raw_probability_exposed`, `risk_category`.
2. `risk_factors` 응답의 최종 구조 확정: `items`, `display_name`, `message`, `source`, `status`.
3. `MODEL_AGE_OUT_OF_RANGE`와 `MODEL_POPULATION_OUT_OF_SCOPE`가 실제 백엔드에서 어느 시점에 반환되는지 확인.
4. 기진단 사용자가 예측 제외 후 접근 가능한 일반 챌린지·건강교육 범위 확정.
5. 모바일·키보드·큰 글씨·명암 대비를 실제 브라우저에서 최종 QA.

## 현재 프론트 작업 파일 위치 확인

- 실제 화면 작업 파일은 `src/frontend/` 안에 있다.
- 현재 변경 파일은 `src/frontend/app.js`, `src/frontend/index.html`, `src/frontend/styles.css`다.
- 이 문서는 팀 공유용 산출물이므로 `docs/`에 둔다.
