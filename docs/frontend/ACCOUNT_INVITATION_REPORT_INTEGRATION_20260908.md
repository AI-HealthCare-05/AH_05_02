# 계정·초대·리포트 프론트 연동 기록 (2026-09-08)

## 반영한 기능

- 로그아웃: `POST /api/v1/auth/logout`
  - 성공 또는 이미 만료된 세션(401)이면 프론트 인증 상태와 임시 건강정보를 정리하고 로그인 화면으로 이동
- 회원탈퇴: `DELETE /api/v1/users/me`
  - 사용자가 `탈퇴`를 직접 입력해야 요청 가능
  - 성공 후 로그아웃을 시도하고 프론트 인증 상태를 정리
- 받은 초대 목록과 수락
  - `GET /api/v1/invitations`
  - `POST /api/v1/invitations/accept`
  - 목록에는 원문 초대 코드가 없으므로 전달받은 코드를 직접 입력하거나 `invite_token` URL 파라미터로 전달
- 초대 코드 발급
  - `POST /api/v1/invitations`에 초대받을 이메일과 현재 지원 관계 유형인 `family`를 전송
  - 응답의 `token`은 사용자 화면에서 `초대 코드`로 표현하고 같은 카드의 코드·복사 영역에 표시
  - 실제 발급값과 혼동되던 로컬 `DEMO-CODE`, 이메일/코드 선택 탭, 미구현 이메일 발송 표현 제거
  - 함께하기 첫 화면에서는 `받은 초대`와 `초대하기`를 작은 카드 두 개로 나란히 표시
  - 두 카드 중 하나를 선택하면 해당 내용만 펼치고, 다른 내용은 접어서 화면 점유를 줄임
  - 초대 링크의 `invite_token`이 있으면 받은 초대 패널을 자동으로 열고 입력값을 유지
- 지난 4주·전체 리포트
  - `GET /api/v1/reports?period=four-week`
  - `GET /api/v1/reports?period=all`
  - `GET /api/v1/reports/{report_id}/cycles?cursor={cursor}`
  - 로딩·빈 결과·실패·재시도·전체 회차 더보기 처리
  - `frequency=unconfirmed` 챌린지는 임의 달성률 없이 기록 횟수만 표시
- PDF는 백엔드 계약대로 이번 주만 활성화
  - `GET /api/v1/weekly-reports/current/pdf`
  - 지난 4주·전체 PDF는 요청하지 않고 미지원 안내 표시

## 8022 실제 서버 확인

- `GET /api/v1/weekly-reports/current` → 401: 경로 마운트 확인
- `POST /api/v1/auth/logout` → 401: 경로 마운트 확인
- `GET /api/v1/users/me` → 401: 경로 마운트 확인
- `GET /api/v1/invitations` → 401: 경로 마운트 확인
- `POST /api/v1/invitations/accept` → 401: 경로 마운트 확인
- `GET /api/v1/reports?period=four-week` → 404: 신규 리포트 백엔드가 현재 8022 서버에는 아직 반영되지 않음

인증이 필요한 경로에서 토큰 없이 받은 401은 경로가 존재한다는 확인이며 기능 실패가 아니다. 신규 리포트 경로의 404는 빛샘님 구현 브랜치 또는 커밋을 8022 실행 코드에 반영해야 해결된다.

## 다음 추가 제언 — 이메일 초대

현재 `POST /api/v1/invitations`는 수신 이메일에 연결된 초대 코드를 반환하지만 메일을 직접 발송하지 않는다. 실제 메일 발송 API 또는 초대 링크 발송 기능이 구현되면 `이메일로 초대`를 별도 선택지로 다시 추가한다. 이때 프론트 연결 전에 발송 성공 여부, 재발송 제한, 7일 만료, 만료·수락 완료 링크 처리, `invite_token` 딥링크 형식을 백엔드 계약으로 확정한다.

## 검증 결과

- 프론트 Node 테스트 62개 통과
- 프론트·프로토타입 Python 테스트 38개 통과
- 브라우저 제어 응답 테스트 통과
  - 받은 초대 조회·초대 코드 수락
  - 받은 초대·초대하기 접이식 카드 전환과 `aria-expanded` 상태
  - 초대 코드 발급 후 같은 카드 표시·복사 활성화
  - 로그아웃 API 호출 및 로컬 세션 정리
  - 회원탈퇴 명시적 확인 및 로컬 세션 정리
  - 지난 4주 참여일/실천일 표시
  - 전체 회차 커서 페이지네이션
  - 모바일 380px 화면 넘침 없음
  - 지난 4주·전체 PDF 요청 차단

## 남은 차단 사항

빛샘님 회신 문서에는 신규 리포트 구현이 완료된 것으로 적혀 있으나, 2026-09-08 원격 갱신 후에도 `origin/fix/e2e-integration-signup-and-worker-deps` 및 다른 원격 브랜치에서 `app/services/reports.py`, `app/apis/v1/reports_routers.py`를 찾을 수 없었다. 해당 커밋이 원격에 올라오면 현재 프론트 코드로 실제 계정의 세 기간을 재검증한다.
