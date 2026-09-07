# 빛샘님 전달용 — 프론트 연결을 위해 필요한 백엔드 확인 사항

빛샘님, 9/7 프론트와 8022 로컬 통합 흐름을 점검한 결과입니다.  
프론트는 가입 → 건강정보 → 오늘이·내일이 결과 → 챌린지 → 대시보드까지 실제 가상 계정으로 통과했습니다. 아래는 백엔드 계약 또는 공통 실행 환경에서 확인이 필요한 항목입니다.

## P0 — 공통 실행 환경·예측 큐

- [ ] 팀에서 사용할 최신 백엔드 브랜치·커밋 SHA, DB 마이그레이션, 워커 이미지와 실행 순서를 공유해 주세요.
- [ ] API와 워커가 같은 Redis host/port/database/stream/group을 사용하는지 확인해 주세요.
- [ ] 현재 확인한 구버전 Docker 워커는 `ai_jobs`, 8022 API는 `prediction_jobs`를 사용했습니다. 작업·결과 저장 테이블 계약을 하나로 맞춰 주세요.
- [ ] 기존 `queued` 작업을 재처리할지, 실패/만료 처리 후 새 작업을 만들지 정책이 필요합니다.
- [ ] worker가 처리한 `model_key`, `task_type`, `model_version`, `threshold_scope`, `threshold_version`, artifact digest, 입력 snapshot ID가 작업과 결과에 동일하게 남는지 확인해 주세요.

로컬에서는 프로젝트 Redis 6380의 전용 스트림과 현재 코드의 로컬 워커로 복구하여 오늘이·내일이 모두 `succeeded`를 확인했습니다. 다른 큐 메시지나 Docker 워커는 삭제·변경하지 않았습니다. 이 로컬 복구는 팀 공통 환경 수정 완료를 뜻하지 않습니다.

## P1 — 회원가입·프로필·동의

- [ ] `/auth/signup` 정식 요청 필드를 확정해 주세요. 현재 DTO는 `email`, `password`, `terms_agreed`이고 프론트는 `birth_date`, `gender`도 보내지만 이후 `/users/me/profile`에 다시 저장합니다.
- [ ] 생년월일·성별을 signup에서 받을지, profile PATCH에서만 받을지 한 가지 계약으로 정리해 주세요.
- [ ] **정확히 만 14세가 되는 생일 당일 `/users/me/profile`이 422입니다.** validator의 `<` 비교와 서비스의 `age >= 14` 기준을 일치시켜 주세요.
- [ ] 만 14세 미만을 계정 생성 전 차단하려면 signup 요청에 생년월일이 필요합니다. 현재처럼 프로필 저장 단계에서 차단할지 정책을 확정해 주세요.
- [ ] 이메일·비밀번호·약관 오류를 필드별 구조화 코드로 내려 주세요. 예: `field`, `code`, `message`, `retryable`. 비밀번호 값 자체는 오류·로그에 포함하지 말아 주세요.
- [ ] 서비스 약관 동의와 건강정보 처리 동의의 저장 필드·버전·시각·철회 계약을 확인해 주세요.
- [ ] 가입은 성공했지만 자동 로그인·프로필·동의 중 일부만 실패한 상태를 조회하고 중복 생성 없이 재시도할 계약이 필요합니다.

## P1 — 이용 대상·의료 안전

- [ ] 현재 코드의 적용 구간은 14~18세 챌린지, 19~44세 오늘이, 45~105세 오늘이+내일이, 106세 이상 내일이 제외입니다. 최종 가입 연령·모델 적용 연령·상한 포함 여부를 확정해 주세요.
- [ ] `reason_codes`, `next_action`, `challenge_eligible`, `current_health_check_eligible`, `future_prediction_eligible`를 응답의 고정 계약으로 사용해도 되는지 확인해 주세요.
- [ ] **당일 진료 필요**는 프론트에서 분기하지만 현재 `EligibilityCreateRequest`에는 별도 필드가 없습니다. 서버 저장 필드와 최근 분기 복원 방법이 필요합니다.
- [ ] 긴급 증상·기진단 사용자의 모델 작업/챌린지 차단이 서버에서도 항상 적용되도록 확인해 주세요.
- [ ] 고위험 신호 사용자는 결과를 진단으로 단정하지 않고 검사·의료기관 안내를 먼저 보게 해야 합니다. 안내 확인 전·후 챌린지 허용 기준을 응답 필드로 고정해 주세요.
- [ ] 안전 분기 후 의료 안내 확인 상태와 챌린지 재진입 허용 기준을 `follow-up-actions` 계약과 맞춰 주세요.

## P1 — 오늘이 세부 입력 스냅샷

- [ ] `POST /api/v1/current-screening-inputs`가 현재 OpenAPI에 없고 404입니다. endpoint 추가 여부와 요청·응답 DTO를 확정해 주세요.
- [ ] 최소 요청 후보: `health_checkup_id`, `input_as_of_date`, 모델 추가 입력, `input_schema_version`.
- [ ] 성공 응답에 `current_screening_input_id`, `validation_status`, `missing_fields`, snapshot version을 부탁드립니다.
- [ ] `POST /prediction-jobs`의 오늘이 요청에서 `current_screening_input_id`가 필수인지 선택인지, 없을 때 오류 코드를 확정해 주세요.
- [ ] 입력 오류는 `422 ML_INPUT_INVALID`, 모델 파일/계약 오류는 `503 MODEL_UNAVAILABLE`·`503 MODEL_CONTRACT_INVALID`로 구분해 주세요.
- [ ] 누락값을 임의로 0으로 만들지 않고, 모델 내부 파생 특성은 외부 입력·DB에 저장하지 않는 원칙을 유지해 주세요.
- [ ] 최종 7변수/22개 입력 중 어떤 계약을 MVP에서 사용할지 준혁님 모델 계약과 함께 확정해 주세요. 확정 전 프론트 세부 항목 삭제는 보류합니다.

## P1 — 예측 응답·표시 안전

- [ ] 오늘이·내일이 각각 아래 메타데이터를 작업·결과 응답에 고정해 주세요: `model_key`, `task_type`, `model_version`, `threshold_scope`, `threshold_version`, 입력 snapshot ID, artifact digest.
- [ ] `status` 허용값과 `prediction_id`, `error_code`, `retryable`, `retry_after_seconds` 계약을 문서화해 주세요.
- [ ] 위험 범주 허용값은 `low/caution/high`로 고정하고 알 수 없는 값은 성공으로 내려주지 말아 주세요.
- [ ] `display_allowed`와 `operational_model_activated`를 별도 boolean으로 유지해 주세요. 둘 중 하나라도 false이면 프론트는 수치·확률·위험요인을 숨깁니다.
- [ ] 연구·운영 미승인 문구와 진단 아님 안내 문구의 버전 또는 응답 필드를 확정해 주세요.
- [ ] 오늘이와 내일이 점수를 합산·평균하지 않습니다. `cumulative_risk_signal`을 개인 확정 발병확률로 표현하지 않는 계약을 확인해 주세요.
- [ ] 모레노는 연구용이며 이번 MVP API 호출·화면에서 제외합니다. 내일이의 지점별 `signal_level`을 유지할지는 모레노 제외와 별도로 확정해 주세요.
- [ ] 생존 곡선·2/4/6년 그래프는 `risk_curve_status=available`, `lower/upper`, calibration, 의료 안전 검토 전까지 공개하지 않습니다.

실제 로컬 추론에서 오늘이 `knhanes-shared7-sk180-research-v1`, 내일이 `rf25-first-interval-survival-ensemble-v1`이 각각 성공했고 `display_allowed=false`, `operational_model_activated=false`가 유지됐습니다.

## P2 — 챌린지 연결

- [ ] `/challenge-recommendations`의 `prediction_id`는 정수만 허용하고, 결과 미제공 사용자에게는 생략 가능한지 확정해 주세요.
- [ ] 추천 결과의 `personalized`, `medical_guidance_required_first`, `items` 필드를 고정해 주세요.
- [ ] 진행 중 사이클 생성 시 409 오류 코드 `ACTIVE_CHALLENGE_CYCLE_EXISTS`와 `/challenge-cycles/current` 복구 계약을 유지해 주세요.
- [ ] 의료 안내 확인 전 챌린지 시작을 서버에서도 차단할지 확정해 주세요.
- [ ] 맞춤 챌린지는 현재 저장 API가 없어 화면에서 시작을 차단합니다. MVP 포함 여부와 저장 endpoint가 필요합니다.

## P2 — 병원·응급기관·지도

- [x] 서울시청 가상 좌표 기준 병원 15곳·응급기관 10곳 REST 목록 HTTP 200 확인.
- [ ] 지도 JavaScript SDK는 HTTP 401 도메인 접근 거부입니다. 카카오 앱 허용 도메인에 `http://127.0.0.1:8022`, `http://localhost:8022` 등록을 확인해 주세요.
- [ ] REST 키를 프론트 JavaScript에 전달하지 말아 주세요. 지도용 JavaScript 키와 서버 REST 키를 분리해 주세요.
- [ ] 키 누락·인증 실패·시간 초과·외부 서비스 오류·결과 없음의 공통 오류 구조를 부탁드립니다.
- [ ] 응급기관 정보가 실시간 수용 가능을 보장하지 않는다는 안전 문구와 데이터 갱신 시각을 응답에 포함할지 확인해 주세요.

## P2 — 주간 리포트·PDF

- [x] `GET /weekly-reports/current/pdf` HTTP 200과 실제 A4 파일 확인. 생활습관 요약·비진단 안내 포함, 모델 확률·위험요인 없음.
- [ ] 긴 요약 문장이 오른쪽에서 잘립니다. 자동 줄바꿈·페이지 여백·한글 폰트 임베딩을 수정해 주세요.
- [ ] PDF에 조회 기간 시작/종료일과 실제 챌린지 수행 기록을 포함해 주세요.
- [ ] ‘이번 주’가 달력 주간인지 최근 7일인지 확정해 주세요. 현재 응답은 최근 7일 표현입니다.
- [ ] ‘4주·전체’ 리포트·PDF endpoint 또는 `period/start_date/end_date` 파라미터 계약이 필요합니다.
- [ ] 기록 없음·권한 없음·생성 실패·재시도 가능 여부의 오류 응답을 구분해 주세요.
- [ ] 향후 오늘이·내일이 블록을 PDF에 넣는다면 화면과 같은 표시 승인 규칙을 서버 PDF 생성에도 적용해 주세요.

## P2 — 건강교육 Q&A

- [ ] `answer_status`, `answer`, `citations`, `medical_notice`, `retrieval_method`의 필수/선택 계약을 확정해 주세요.
- [ ] 빈 답변을 성공으로 보내지 말고 근거 부족·결과 없음·의료 안전 거절·서버 실패를 구분해 주세요.
- [ ] `grounded`이면 안전한 URL을 가진 출처가 최소 1개 있도록 보장해 주세요.
- [ ] 9/7 추가 교육자료가 실행 중인 8022 RAG 인덱스에 포함됐는지 확인해 주세요.

## 프론트에서 완료한 범위

- [x] 가입 → 건강정보 → 오늘이·내일이 결과 → 의료 안내 → 챌린지 → 대시보드 실제 E2E.
- [x] 건강정보 유/무 사용자 첫 화면 분리.
- [x] 로딩·빈 결과·실패·재시도 UI와 모델별 부분 실패 처리.
- [x] 미성년·미동의·응급·당일 진료·기진단·모델 연령 밖 안내 및 키보드 초점 처리.
- [x] 오늘이·내일이 분리, 모레노 MVP 제외, 공개 승인 전 수치·곡선 차단.
- [x] 프론트 PR #23 `a9a0d29` 푸시. Node 51개, pytest 122개, Ruff 검사 통과.

## 공동 완료 조건

- [ ] 위 P0·P1 계약을 최신 백엔드 커밋과 OpenAPI에 반영.
- [ ] 같은 커밋·DB·Redis·worker로 실제 전체 흐름 재검증.
- [ ] 연령·의료 안전·모델 표시 정책에 담당자 승인 기록.
- [ ] 지도 도메인 설정, PDF 레이아웃, 4주·전체 계약까지 재검증.
