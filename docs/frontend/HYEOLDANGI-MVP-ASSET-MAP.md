# 혈당이 MVP 캐릭터 배치표

모든 캐릭터는 단독 투명 RGBA PNG이며, 화면 문구는 이미지 밖의 HTML 텍스트로 제공한다.

## 첫 화면 권장 구성

첫 화면의 큰 안내 캐릭터는 `hyeoldangi-default.png`를 유지한다. 아래 서비스 이용 과정 3개 카드에는 서로 다른 동작을 배치한다.

| 첫 화면 요소 | 권장 자산 | 의미 |
| --- | --- | --- |
| 큰 환영·안내 | `hyeoldangi-default.png` | 인사하며 서비스 전체 안내 |
| 건강정보 입력 | `hyeoldangi-health-input.png` | 체크보드를 직접 탭하는 동작 |
| 결과 확인 | `hyeoldangi-guide.png` | 결과를 차분히 설명하는 동작 |
| 챌린지 시작 | `hyeoldangi-challenge-walking.png` | 작은 실천을 바로 시작하는 동작 |

## 8단계 MVP 흐름

| 단계 | 화면 | 주 자산 | 보조·상태 자산 |
| --- | --- | --- | --- |
| 1 | 서비스 안내 | `hyeoldangi-default.png` | `hyeoldangi-health-input.png`, `hyeoldangi-guide.png`, `hyeoldangi-challenge-walking.png` |
| 2 | 가입·동의 | `hyeoldangi-consent.png` | 개인정보와 동의를 겁주지 않고 표현 |
| 3 | 적합성·안전 확인 | `hyeoldangi-eligibility.png` | 확인 후 진행하는 차분한 손짓 |
| 4 | 건강정보 입력·검토 | `hyeoldangi-health-input.png` | 건강·생활습관 항목을 입력·점검 |
| 5 | 분석 상태 | `hyeoldangi-default.png` | 대기: 기본 / 분석 중: `hyeoldangi-analyzing.png` / 완료: `hyeoldangi-complete.png` / 실패·지연: `hyeoldangi-guide.png` |
| 6 | 위험 결과·생활습관 방향 | 위험 범주 3종 | `hyeoldangi-risk-low.png`, `hyeoldangi-risk-caution.png`, `hyeoldangi-risk-high.png` |
| 7 | 4주 챌린지 선택 | 챌린지 4종 | 걷기·식사·물·정기점검 자산을 카드 종류에 맞게 사용 |
| 8 | 건강 홈·대시보드 | `hyeoldangi-daily-record.png` | 오늘 할 일과 기록 진입을 안내 |

## 챌린지·대시보드 세부 기능

| 기능 | 권장 자산 | 파일명 |
| --- | --- | --- |
| 가볍게 걷기 | 신발 없이 한 발을 내딛는 혈당이 | `hyeoldangi-challenge-walking.png` |
| 식사 리듬 | 균형 접시를 두 손으로 제시 | `hyeoldangi-challenge-meal.png` |
| 덜 달게 마시기 | 물컵을 들고 작은 선택 표현 | `hyeoldangi-challenge-water.png` |
| 정기 점검 | 달력과 워치를 함께 확인 | `hyeoldangi-challenge-checkup.png` |
| 오늘 기록 | 휴대폰 체크 버튼을 직접 탭 | `hyeoldangi-daily-record.png` |
| 목표 조정 | 목표 단계를 낮춰 다시 시작 | `hyeoldangi-goal-adjust.png` |
| 주간 리포트 | 생활습관 체크 흐름 발표 | `hyeoldangi-report.png` |
| 완료 축하 | 양손을 들고 체크와 함께 축하 | `hyeoldangi-complete.png` |
| 꾸준한 응원 | 엄지척과 파이팅 | `hyeoldangi-cheer.png` |
| 함께하기 | 하트 토큰을 밖으로 전달 | `hyeoldangi-together.png` |
| 워치 연동 | 워치를 앞으로 내밀어 연결 표현 | `hyeoldangi-wearable.png` |
| 건강정보 다시 입력 | 체크보드를 탭해 수정·재확인 | `hyeoldangi-health-input.png` |
| 생활습관 Q&A | 책을 펼치고 근거 자료 안내 | `hyeoldangi-question.png` |

## 당근의 숲 함께하기 상태

| 상태 | 권장 자산 | 표현 |
| --- | --- | --- |
| 당근의 숲 대표·오늘의 상징 | `hyeoldangi-forest-carrot.png` | 한 손에 당근을 들고 반대 손을 높이 들어 소개 |
| 가족·친구와 함께하는 중 | `hyeoldangi-forest-family-friends.png` | 서로 기대어 응원하는 혈당이 3인 그룹 |
| 새로운 가족·친구 초대 | `hyeoldangi-forest-invite.png` | 사람 추가 아이콘과 당근 봉인이 있는 초대장을 건넴 |

## 사용 원칙

- 캐릭터 이미지는 제목이나 설명을 대신하지 않는다. 의미 있는 대체 텍스트를 함께 제공한다.
- 위험 범주는 색만으로 구분하지 않고 화면 제목·범주명·행동 안내를 함께 제공한다.
- 위험 높음 캐릭터도 응급·확진 표현으로 사용하지 않는다.
- 동일 화면에서 큰 캐릭터는 1개를 원칙으로 하고, 작은 과정 카드에서는 최대 3개까지만 사용한다.
- 캐릭터가 들고 있는 카드에는 의료 수치나 진단 문구를 넣지 않는다.
