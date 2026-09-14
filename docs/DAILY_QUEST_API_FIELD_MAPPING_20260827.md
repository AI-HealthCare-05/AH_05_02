# 일일 퀘스트 화면·API 필드 대조

| 화면 항목 | API 필드 | 저장 위치 | 완료 기준 |
|---|---|---|---|
| 퀘스트 이름 | `current_cycle.user_challenges[].title` | `challenges` | 서버 카탈로그를 원본으로 사용 |
| 일일 완료 | `is_completed`, `value`, `source` | `challenge_logs` | 사용자·챌린지·날짜당 1건 |
| 사진·위치 인증 | `verification_type`, `evidence_ref`, `evidence_digest`, `location_accuracy_m` | `challenge_verifications` | 인증 유형별 필수 증빙 확인 |
| 식사 사진 | multipart `file`, `verification_date` | `challenge_verifications`, `challenge_verification_events` | 채소 탐지 승인 시만 완료 로그 생성 |
| 일일 보상 | `eligible`, `claimed`, `carrot_amount` | `daily_challenge_rewards`, `reward_transactions` | 선택한 챌린지를 전부 완료 후 1회 (선택 개수는 사용자마다 다를 수 있음, 고정 3개 아님) |
| 개인 수행률 | `recent_7_days`, `four_weeks` | 대시보드 집계 | 오늘까지의 완료/계획 건수 |
| 공동 목표 | `shared_goals.groups[]` | 공동 챌린지 집계 | 수행 상태만 공유 |
| 보유 당근 | `carrot_balance` | `user_wallets` | 보상 원장의 `balance_after`와 일치 |
| 인벤토리·아바타 | `item_id`, `quantity`, `equipped_item_ids`, `version` | `user_inventory`, `user_avatars` | 보유 아이템만 장착 |

## 연결 API

- `GET /api/v1/challenge-cycles/current`
- `PUT /api/v1/user-challenges/{id}/logs/{date}`
- `POST /api/v1/user-challenges/{id}/verifications`
- `POST /api/v1/user-challenges/{id}/meal-photo-verifications`
- `GET|POST /api/v1/daily-challenge-rewards/{date}`
- `GET /api/v1/dashboard/challenge-progress`
- `GET /api/v1/wallet`, `GET /api/v1/inventory`, `PUT /api/v1/avatar/equipment`
