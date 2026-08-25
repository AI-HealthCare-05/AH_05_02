# 간당간당 기능 확장 구현 구성 — 2026-08-21

## 구현 목표

기존 핵심 사용자 흐름을 유지하면서 행동변화와 가족·친구 함께하기 기능을 추가한다.

```text
위험 선별
  → 규칙 기반 챌린지 추천
  → 4주 챌린지·일일 기록
  → 실패 원인·목표 조정
  → 주간 리포트·4주 교육
  → 가족·친구 초대·연결
  → 공동 챌린지·응원
```

## 코드 구성

| 계층 | 파일 | 책임 |
| --- | --- | --- |
| Router | `app/apis/v1/engagement_routers.py` | 행동변화·함께하기 HTTP API |
| DTO | `app/dtos/engagement.py` | 입력 범위·관계·기간·중복 검증 |
| Service | `app/services/engagement.py` | 주간 집계, 교육, 초대, 연결, 공동 챌린지 정책 |
| Repository | `app/repositories/engagement_repository.py` | 신규 엔터티 조회·저장과 소유권 범위 조회 |
| Model | `app/models/engagement.py` | 행동변화·함께하기 DB 모델 |
| Migration | `app/core/db/migrations/models/3_20260821223000_engagement_and_together.py` | 신규 테이블 생성·롤백 |
| Frontend | `src/frontend/index.html`, `app.js`, `styles.css` | 대시보드에서 새 기능 직접 사용 |
| Test | `tests/test_engagement_integration.py` | 초대부터 공동 챌린지·응원까지 통합 검증 |

## 구현된 기능

### 행동변화

- 건강정보 기반 규칙형 챌린지 최대 3개 추천과 추천 사유
- 챌린지 실패 원인 기록과 안전한 목표 조정안
- 최근 7일 달성률·잘한 습관·지원 필요 습관·다음 조정안
- CDC PreventT2 기반 4주 교육 카드와 확인 퀴즈
- 교육 콘텐츠 완료 이력

### 가족·친구 함께하기

- 이메일 대상 일회용 초대 토큰 생성
- 초대 토큰은 해시만 DB에 저장하고 원문은 생성 응답에서 한 번만 제공
- 초대받은 이메일 계정만 수락 가능
- 가족·친구·보호자 관계 설정
- 기본 공유 범위는 `challenge_status` 하나로 제한
- 공동 챌린지 생성 후 상대방 별도 참여 수락
- 참여자별 개인 목표와 공동 목표
- 미리 검토된 응원 문구만 전송
- 건강정보·예측 결과·내부 점수는 자동 공유하지 않음

## 주요 API

| Method | Endpoint | 기능 |
| --- | --- | --- |
| POST | `/api/v1/user-challenges/{id}/barriers` | 미실천 원인과 조정안 기록 |
| GET | `/api/v1/weekly-reports/current` | 최근 7일 주간 리포트 |
| GET | `/api/v1/education-contents` | 4주 교육 콘텐츠·진행 상태 |
| PUT | `/api/v1/education-contents/{id}/progress` | 퀴즈 답변과 완료 기록 |
| POST | `/api/v1/invitations` | 가족·친구 초대 생성 |
| GET | `/api/v1/invitations` | 보낸·받은 초대 조회 |
| POST | `/api/v1/invitations/accept` | 초대 수락·연결 생성 |
| GET | `/api/v1/connections` | 연결 관계·공유 범위 조회 |
| POST | `/api/v1/shared-challenge-groups` | 공동 챌린지 초대 생성 |
| POST | `/api/v1/shared-challenge-groups/{id}/accept` | 공동 챌린지 참여 수락 |
| GET | `/api/v1/shared-challenge-groups` | 공동 진행 현황 조회 |
| POST | `/api/v1/shared-challenge-groups/{id}/encouragements` | 검토된 응원 보내기 |

## 신규 엔터티

- `ChallengeBarrier`
- `EducationContent`
- `ContentProgress`
- `Invitation`
- `Connection`
- `SharedChallengeGroup`
- `SharedChallengeMember`
- `Encouragement`

## 개인정보·의료 안전 결정

- 가족 연결과 건강정보 공유를 동일한 동의로 처리하지 않는다.
- 현재 기본 공유는 챌린지 수행 상태만 허용한다.
- 공동 챌린지는 연결 후에도 참여자가 별도로 수락해야 한다.
- 사진 공유와 자유 메시지는 신고·차단·보관 정책 전에는 제공하지 않는다.
- 몸이 불편한 미실천 사유에는 목표 강행 대신 중단과 의료진 상담 문구를 제공한다.
- 주간 달성률은 질병 위험 감소·진단·치료 효과로 표현하지 않는다.

## 후속 구현

- 연결 해제·차단과 공유 범위 변경 API
- 공동 챌린지 생성·응원 전용 화면
- 생활습관 통합 기록과 대신 입력 감사 로그
- 주간 보고서 스냅샷·PDF 생성
- 배지·연속 실천일
- 운영 배포 후 P95 부하시험과 보안 점검
