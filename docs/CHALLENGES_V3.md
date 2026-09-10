# 챌린지 V3 구현·안전·API 공유 문서

작성 기준: 2026-09-08 구현·로컬 검증 결과. 카탈로그 버전은 `evidence-v3`이며 PR 리뷰 전 초안이다. 이 문서는 배포 완료, 의료적 효과 또는 사진 모델의 정확도를 보증하지 않는다.

- 검토 PR: [Draft PR #40](https://github.com/AI-HealthCare-05/AH_05_02/pull/40)
- 관련 이슈: [#39](https://github.com/AI-HealthCare-05/AH_05_02/issues/39)

## 1. 이번 변경의 핵심

새 V3 사이클은 매일 **음료 선택 1개 + 식이섬유 중심 식사 1개 + 유산소 활동 1개**, 총 3개의 챌린지로 구성한다. 식단 위주·운동 위주를 선택해도 다른 영역을 없애거나 하루 챌린지 개수를 바꾸지 않는다. 선택한 구성으로 새 4주 사이클을 시작하며 기간은 시작일을 포함한 28일이다.

사용자의 중점 영역과 실천 난이도는 식단의 실천 끼니 수와 운동의 누적 시간을 조절한다. 반면 **1·2·3유형은 인증 방식이지 난이도 순서가 아니다.**

이번 추천은 공식 자료를 참고해 미리 작성한 후보를 규칙으로 조합한다. 매번 새로운 챌린지를 AI/RAG로 생성하거나 개인 건강정보에 맞는 의료 처방을 산출하지 않는다. API도 `source_backed_rule_based`, `personalized: false`, `preference_applied: true`로 이를 구분한다.

기존 사이클·기록과 기존 게임을 유지한다. **밭·당근 보상 방식은 아직 미정이므로 V3 전용 보상, 지급량 변경, 새 게임 또는 새 지급 연동은 구현하지 않았다.** 음료 기록 후 보이는 “당근에 물을 주었습니다”는 게임 응원 문구이며 실제 수분 섭취량이나 추가 보상 지급을 의미하지 않는다.

## 2. 중점 영역과 난이도별 일일 목표

`focus`는 `balanced`(균형), `diet`(식단 위주), `activity`(운동 위주)이며, `difficulty`는 `easy`(쉬움), `moderate`(보통), `advanced`(도전)이다.

균형은 두 영역에 선택한 단계를 그대로 적용한다. 중점 영역을 지정하면 해당 영역은 선택한 단계, 다른 영역은 한 단계 낮게 제안한다. 쉬움보다 더 낮추지는 않는다. 음료 선택은 모든 조합에서 같은 공통 목표다.

| 중점 영역 | 선택 난이도 | 식단 실천 목표 | 유산소 활동 목표 |
| --- | --- | --- | --- |
| 균형 `balanced` | 쉬움 `easy` | 하루 1끼 | 하루 누적 10분 |
| 균형 `balanced` | 보통 `moderate` | 하루 2끼 | 하루 누적 20분 |
| 균형 `balanced` | 도전 `advanced` | 하루 3끼 | 하루 누적 30분 |
| 식단 위주 `diet` | 쉬움 `easy` | 하루 1끼 | 하루 누적 10분 |
| 식단 위주 `diet` | 보통 `moderate` | 하루 2끼 | 하루 누적 10분 |
| 식단 위주 `diet` | 도전 `advanced` | 하루 3끼 | 하루 누적 20분 |
| 운동 위주 `activity` | 쉬움 `easy` | 하루 1끼 | 하루 누적 10분 |
| 운동 위주 `activity` | 보통 `moderate` | 하루 1끼 | 하루 누적 20분 |
| 운동 위주 `activity` | 도전 `advanced` | 하루 2끼 | 하루 누적 30분 |

음료 공통 목표는 “당 음료 대신 물을 선택했거나, 당 음료를 마시지 않았거나, 개인 수분 지침을 지켰는지 하루 1회 확인”이다. 물의 양을 늘리는 과제가 아니다. 메타데이터에는 음료의 `difficulty`가 `easy`로 들어가지만 `always_include: true`이며 정책의 해당 영역은 `common`으로 표시한다.

**1·2·3끼 및 10·20·30분은 서비스가 정한 단계별 제품 목표다. 연구에서 검증한 개인별 처방량, 권장 식사 횟수 또는 치료 목표가 아니다.** 식단 목표는 평소 식사 안에서 실천한 끼니 수이며, 목표를 채우려고 식사량이나 끼니를 늘리거나 끼니를 거르지 않는다. 운동은 나누어 누적할 수 있다. 개인 치료식·수분 제한·운동 제한과 의료진 지침을 우선하고, 통증·어지럼·심한 호흡곤란이 있으면 중단한다.

## 3. 카탈로그와 후보 새로고침

카탈로그에는 공통 음료 1개, 식단 2종 × 3단계, 운동 2종 × 3단계로 총 13개 항목이 있다. 아래 `{단계}`는 각각 `easy`, `moderate`, `advanced`를 뜻한다.

| 영역 / API domain | 후보와 코드 | 항목 수 | 인증 방식 |
| --- | --- | --- | --- |
| 음료 / `hydration` | 당 음료 대신 물·개인 수분 지침 확인 — `v3_hydration_choice` | 1 | 3유형 |
| 식단 / `fiber_diet` | 채소 반찬을 포함한 식사 — `v3_vegetable_{단계}` | 3 | 1유형 |
| 식단 / `fiber_diet` | 정제 곡물 일부를 통곡물·콩류로 바꾸기 — `v3_wholegrain_{단계}` | 3 | 2유형 |
| 운동 / `aerobic_activity` | 내 몸에 맞게 꾸준히 걷기 — `v3_walk_{단계}` | 3 | 2유형 |
| 운동 / `aerobic_activity` | 실내에서 유산소 활동 이어가기 — `v3_indoor_aerobic_{단계}` | 3 | 2유형 |

“다른 후보 보기”는 유한한 후보를 순환한다. 고정된 선호·난이도에서 식단 2종과 운동 2종을 조합하므로 같은 후보가 반복될 수 있다. `rotation`은 조합 선택용 값이지 횟수별 보상이나 새 콘텐츠 생성 횟수가 아니다. 화면에는 새로고침 사용 횟수 제한을 두지 않으며 요청값은 허용 범위 안에서 순환한다.

실제 사진 검토 설정이 없으면 채소 확인형 후보 대신 같은 단계의 통곡물·콩류 사진 제출형을 제안한다. 따라서 검토 미연결 환경에서는 후보 종류가 더 적다. 이 경우에도 하루 3영역 구성과 목표 단계는 유지한다.

새로고침은 새 사이클을 위한 후보만 바꾸며 기존 사이클, 완료 기록, 인증 증빙, 보상을 수정하지 않는다. 기존 사이클은 새 후보로 자동 변환하지 않는다. 버전별 코드는 기존 목표를 덮어쓰지 않는 방식으로 등록하며, 향후 목표 변경은 새 버전·코드로 관리한다. 진행 중인 사이클이 있으면 추가 사이클 생성은 거절한다.

## 4. 인증 유형과 실제 확인 범위

| 유형 | 사용자가 제출하는 것 | 서버가 확인하는 것 | 확인하지 않는 것 |
| --- | --- | --- | --- |
| 1유형: 사진 + 채소 확인 | 대표 식사 사진 1장과 실제 실천 끼니 수 | 유효한 이미지, 자기보고 값이 목표 이상인지, 실제 이미지 검토 결과의 채소 포함 여부 | 실제 섭취, 모든 끼니의 실천, 섭취량, 비전분 채소의 정확한 종류, 영양성분·칼로리·치료 효과 |
| 2유형: 사진 제출 | 대표 사진 또는 활동 기록 화면 1장과 실제 끼니 수·활동 시간 | 유효한 이미지가 제출됐는지와 자기보고 값이 목표 이상인지 | 통곡물 여부, 실제 활동·섭취, 운동 시간의 진위, 위치·촬영 시점, 영양성분·치료 효과 |
| 3유형: 자가 체크 | 음료 선택·개인 수분 지침 실천 체크 | 본인의 체크 기록 | 물 섭취량 또는 의료적 적합성의 자동 판정 |

사진형의 실천량은 본인 기록이다. 예를 들어 하루 3끼 목표를 대표 사진 1장으로 제출하더라도 사진 세 끼를 확인한 것이 아니다. 이미지 해시는 인증 식별용이며 같은 사진의 다른 날 재사용이나 실제 촬영 사실을 판별하는 장치가 아니다.

1유형은 채소 포함 값이 실제 boolean `true`이고 confidence가 유한한 0~1 범위의 숫자이며 0.5 이상일 때 승인한다. 이 수치는 구현상의 판정 경계이지 검증된 정확도나 성공 확률이 아니다. 문자열 `"false"`, boolean을 숫자로 해석한 값, NaN·무한대·범위를 벗어난 값은 정상 판정으로 받아들이지 않는다. 설정과 provider·결과의 종류 모두 실제 OpenAI 이미지 검토 경로여야 하며 개발용 mock의 성공을 V3 완료로 사용하지 않는다.

채소 포함을 확인하지 못한 정상 응답은 HTTP 200의 `review_status: "needs_review"`, `challenge_completed: false`로 반환한다. 오류 상태와 혼동하지 않고 완료로 표시하지 않아야 한다. 2유형의 `accepted`는 사진 제출 접수를 뜻하며 AI 내용 검증 성공이 아니다.

사진형에는 간편 체크로 완료하는 우회 경로를 제공하지 않는다. 로컬 화면 미리보기에서도 실제 사진 인증 성공이나 새 보상 지급을 만들어내지 않는다.

### 사진 및 개인정보 처리

- 업로드는 기본 최대 8MB, 최대 1,200만 화소의 JPG·PNG·WEBP를 허용한다. 파일명이나 MIME 선언만 믿지 않고 이미지를 실제로 읽어 형식·크기를 확인한다. 바이트 제한은 서버의 `FOOD_PHOTO_MAX_BYTES` 설정을 따른다.
- 이미지 메타데이터를 제거하고 RGB JPEG로 다시 만든 뒤 최대 1600 × 1600 범위로 축소한다. 원래 파일명과 EXIF 위치정보를 외부 검토 요청에 전달하지 않는다.
- V3 구현은 원본·변환 이미지 파일을 영구 저장하지 않는다. DB에는 날짜, 인증 상태·해시, 이벤트 이력, 자기보고 실천량 등의 기록만 남긴다. 이는 업로드·요청 처리 중 메모리나 임시 파일을 전혀 사용하지 않는다는 뜻은 아니다.
- 1유형은 변환한 사진을 외부 OpenAI 이미지 검토 서비스에 전송한다. 2유형은 외부 이미지 판정 요청을 하지 않는다. 얼굴·주소·이름 등 사진 안에 보이는 개인정보는 자동 삭제하지 않으므로 촬영 안내가 필요하다.
- **운영 전 외부 provider의 보관·삭제·이용 정책, 처리 위치, 사용자 고지·동의 및 관련 처리 절차를 확인해야 한다.** 서비스 내부의 이미지 미보관 구현을 외부 provider까지 포함한 “어디에도 저장되지 않음”으로 표현하지 않는다. 이번 구현을 개인정보 처리 정책 검토 완료로 간주하지 않는다.

## 5. 공식 근거와 제품 목표의 경계

이 카탈로그는 다음 공식 자료의 일반적인 생활습관 원칙을 참고했다. 출처가 있다는 사실은 이 앱의 목표표, 사진 모델 또는 4주 프로그램 효과가 임상적으로 검증되었다는 뜻이 아니다.

| 카탈로그에 반영한 원칙 | 공식 근거와 원문 | 적용 범위 |
| --- | --- | --- |
| 가당 음료를 줄이고 수분이 필요할 때 물을 우선 선택 | [대한당뇨병학회: 당뇨인 제로칼로리 음료 괜찮을까](https://diabetes.or.kr/bbs/?code=news&mode=view&number=2030) | 음료 선택의 방향만 참고한다. 물 섭취량 목표나 제로칼로리 음료의 치료 효과를 만들지 않는다. |
| 채소·통곡물·콩류 등 식이섬유가 있는 식품을 식사에 포함하고 급격한 섭취 증가를 피함 | [미국당뇨병학회 ADA: Get to Know Carbs](https://diabetes.org/food-nutrition/understanding-carbs/get-to-know-carbs) | 식품 선택과 서서히 실천한다는 원칙을 참고한다. 하루 1·2·3끼 목표는 서비스 설계다. |
| 규칙적 유산소 활동과 개인 상태에 맞는 강도·종류 조절 | [대한당뇨병학회: 당뇨병과 운동 FAQ](https://www.diabetes.or.kr/bbs/?category=M&code=faq) | 주 150분 이상 중강도 유산소 활동이라는 일반 안내와 개인 상태 고려를 참고한다. 앱의 10·20·30분은 단계별 제품 목표이며 모두가 주간 권고를 충족한다는 뜻이 아니다. |
| 지속 가능한 식생활 개선과 신체활동, 작은 실천부터 시작 | [NIDDK: Preventing Type 2 Diabetes](https://www.niddk.nih.gov/health-information/diabetes/overview/preventing-type-2-diabetes) | 건강한 식사, 가당 음료 대신 물 선택, 점진적인 활동의 일반 원칙을 참고한다. 문서의 다른 치료·약물 내용을 챌린지로 생성하지 않는다. |

공식 자료에는 당뇨병 환자 대상 설명도 포함되어 있으므로 서비스 이용자에게 치료 지침을 그대로 적용하지 않는다. 기진단 또는 긴급 경고 신호가 있으면 챌린지 진행보다 의료기관 안내가 우선이다. 생성형 AI는 약물 시작·중단·용량 변경을 추천하지 않는다. 제공 결과와 안내는 위험 선별·건강교육·일반 생활 실천이며 진단이나 처방이 아니다.

## 6. API 계약

모든 경로의 접두사는 `/api/v1`이다. 공개 카탈로그 조회를 제외한 아래 API는 `Authorization: Bearer <access_token>` 인증을 사용한다. 성공 응답은 `{ "data": ..., "meta": { "request_id": ..., "timestamp": ... } }` 구조다. 아래 예시 ID는 설명용이며 실제로 조회한 ID를 사용한다. 날짜 예시는 요청 시점의 서울 날짜와 실제 사이클 기간에 맞게 바꾼다.

### 6.1 카탈로그 조회 — GET `/challenges`

`catalog_version=evidence-v3`이면 V3 카탈로그를 반환한다. 생략하면 기존 카탈로그를 반환하여 기존 계약을 유지한다. 미지원 버전은 422다.

```http
GET /api/v1/challenges?catalog_version=evidence-v3
```

`data.items`의 각 항목에는 기존 `challenge_id`, `code`, `title`, `category`, `daily_goal`, `description`, `safety`, `source`와 함께 다음 메타데이터가 들어간다.

- `catalog_version`, `domain`, `difficulty`, 숫자형 `verification_type`, `always_include`
- `goal`: `target_count`, `target_minutes`, `period: "day"`
- `goal_basis`, `verification_scope`, `photo_review_target`, `supporting_sources`, `weekly_guidance`

`category`의 `hydration`·`diet`·`activity`와 `domain`의 `hydration`·`fiber_diet`·`aerobic_activity`를 혼동하지 않는다. 인증 유형 숫자도 기존 인증 DB의 문자열 `verification_type: "photo"`와 다른 용도다.

### 6.2 후보 추천 — GET `/challenge-recommendations`

| 쿼리 | 기본값 / 허용값 | 의미 |
| --- | --- | --- |
| `catalog_version` | 생략 또는 `evidence-v3` | 생략 시 기존 추천 계약 |
| `focus` | `balanced`; `balanced`, `diet`, `activity` | 중점 영역 |
| `difficulty` | `easy`; `easy`, `moderate`, `advanced` | 실천 단계 |
| `rotation` | `0`; 정수 0~1,000,000 | 유한한 후보 조합 순환 |
| `prediction_id` | 선택 정수 | 제공하면 본인 소유 예측인지 확인; V3의 의료적 개인화를 뜻하지 않음 |

```http
GET /api/v1/challenge-recommendations?catalog_version=evidence-v3&focus=diet&difficulty=moderate&rotation=1
Authorization: Bearer <access_token>
```

응답의 `data.items`는 3개다. `data.policy`에는 `focus`, `difficulty`, `domain_levels`, `daily_count: 3`, `rotation`, 안내문이 포함된다. 예를 들어 위 요청의 단계는 음료 `common`, 식단 `moderate`, 운동 `easy`다.

`photo_review_available`은 실제 OpenAI provider 설정과 API 키의 존재 여부를 나타내며 외부 API의 정상 작동·가용성을 사전 보증하지 않는다. `medical_guidance_required_first`가 참이면 의료기관 안내 확인이 먼저 필요하다. `catalog_version`, `recommendation_type`, `personalized`, `preference_applied`, `notice`도 확인한다.

### 6.3 새 사이클 생성 — POST `/challenge-cycles`

기존 요청에 `catalog_version`, `focus`, `difficulty`를 추가했다. V3는 응답에서 받은 V3 ID 3개를 전달해야 하며 음료·식단·운동 각 1개와 선호·난이도별 단계 조합을 서버에서 검증한다. 기존 항목과 V3 항목을 섞거나 V3 버전을 누락해 우회할 수 없다.

```json
{
  "start_date": "2026-09-08",
  "challenge_ids": [101, 105, 108],
  "prediction_id": null,
  "catalog_version": "evidence-v3",
  "focus": "diet",
  "difficulty": "moderate"
}
```

성공은 HTTP 201이며 `data`에 생성된 사이클과 `user_challenges`가 들어간다. 이후 일일 기록은 카탈로그의 `challenge_id`가 아닌 각 선택 항목의 **`user_challenge_id`**를 사용한다. 기존 버전 생략 요청과 기존 사이클의 1~3개 선택 계약은 유지한다. `focus`와 `difficulty`는 생성 검증에 사용하고 실제 선택 항목의 버전 코드가 목표를 고정한다. 사이클 응답에 별도 선호 설정 필드가 저장된다고 가정하지 않는다.

### 6.4 V3 사진 인증 — POST `/user-challenges/{user_challenge_id}/photo-verifications`

요청은 JSON이 아닌 `multipart/form-data`다. 인증 유형은 서버가 선택된 챌린지에서 결정하므로 클라이언트가 `verification_type`이나 판정 결과를 보내지 않는다.

| 필드 | 필수 | 형식 / 검증 |
| --- | --- | --- |
| `verification_date` | 예 | `YYYY-MM-DD`; 서울 기준 오늘 또는 과거이며 허용된 사이클 기간 안의 날짜 |
| `actual_value` | 예 | 유한한 숫자, 요청 범위 0~720, 선택 목표 이상; 식단은 실천 끼니 수, 운동은 누적 분 |
| `file` | 예 | 위 이미지 형식·용량·화소 제한을 만족하는 사진 1장 |

`actual_value`의 720은 입력 경계일 뿐 권장 운동량이나 식사량이 아니다. API는 float를 받으므로 정수형 실천량만 서버에서 강제한다고 설명하지 않는다. 현재 화면은 정수 입력 간격을 사용한다.

브라우저 요청 예시에서 `selectedPhoto`는 사용자가 파일 입력에서 선택한 `File` 객체이며, ID와 날짜는 실제 선택·기간으로 바꾼다. `Content-Type`을 직접 지정하지 않아야 브라우저가 multipart 경계를 붙인다.

```javascript
const form = new FormData();
form.append("verification_date", "2026-09-08");
form.append("actual_value", "20");
form.append("file", selectedPhoto);

await fetch("/api/v1/user-challenges/501/photo-verifications", {
  method: "POST",
  headers: { Authorization: `Bearer ${accessToken}` },
  body: form,
});
```

2유형 사진 제출 성공 응답 예시:

```json
{
  "data": {
    "verification_id": 901,
    "challenge_completed": true,
    "review_status": "accepted",
    "already_recorded": false,
    "notice": "사진 제출을 확인했습니다. 활동 시간·섭취량은 본인 기록이며 AI 검증이 아닙니다."
  },
  "meta": {
    "request_id": "req_example",
    "timestamp": "2026-09-08T03:00:00Z"
  }
}
```

이미 승인·완료된 날짜에 유효한 사진과 실천량을 다시 제출하면 `already_recorded: true`로 기존 `verification_id`를 반환한다. 기존 승인 증빙·실천량·이벤트를 덮어쓰거나 추가 보상을 지급하지 않는다. 이 endpoint 자체에는 보상 지급 호출이 없다. 사진이 바뀌어도 이미 승인된 기록을 새로운 검토 실패로 바꾸지 않는다.

### 6.5 기존 PUT 로그 API 유지

기존 `PUT /user-challenges/{user_challenge_id}/logs/{log_date}`와 `GET /user-challenges/{user_challenge_id}/logs?start_date=...&end_date=...`는 유지한다. V3 3유형 음료 체크도 기존 PUT을 사용한다.

```http
PUT /api/v1/user-challenges/500/logs/2026-09-08
Authorization: Bearer <access_token>
Content-Type: application/json

{"is_completed":true,"value":1,"source":"self_report"}
```

V3 1·2유형을 PUT의 `is_completed: true`로 완료하려 하면 422다. `false`인 미완료 기록 요청까지 금지하는 계약은 아니다. 기존 비V3 챌린지의 기록 방식은 그대로 유지한다. 두 기록 경로 모두 V3에는 동의·이용 대상·의료기관 안내 상태를 확인한다.

### 6.6 상태 코드와 화면 처리

| 코드 | 대표 상황 | 처리 원칙 |
| --- | --- | --- |
| 200 | 조회·로그 저장·사진 제출 응답 | 사진은 코드만 보지 말고 `challenge_completed`와 `review_status` 확인 |
| 201 | 사이클 생성 성공 | 반환된 `user_challenge_id`로 기록 |
| 401 | 만료된 토큰, 인증 사용자 확인 실패 등 | 재로그인; 이전 계정의 늦은 응답을 현재 화면에 반영하지 않음 |
| 403 | 건강정보 동의·이용 대상 확인 부재, 기진단·긴급 경고 신호 등 | 완료 처리하지 않고 필요한 동의·이용 안내 제공 |
| 404 | 본인 소유가 아닌/없는 선택 항목·사이클·예측 | 다른 사용자 데이터 존재를 추정하지 않고 재조회 |
| 409 | 진행 중이 아닌 사이클, 기존 진행 사이클 존재, 미확인 의료기관 안내 | 상태 확인 후 진행; 자동으로 새 사이클 생성·완료하지 않음 |
| 422 | 잘못된 쿼리·조합·날짜·수량·파일, 사진형 PUT 완료 시도 | 입력 또는 기록 방식 수정 |
| 502 | 외부 이미지 검토 실패·잘못된 응답·실제 provider 결과가 아닌 경우 | 완료 처리하지 않음; 원인 확인 후 재시도 |
| 503 | 실제 사진 검토 설정·키 없음, 미연결 상태에서 1유형 선택 | mock 성공이나 자가 체크 완료로 바꾸지 않음; 새 후보는 사진 제출형으로 재조회 가능 |

기존 인증 계층에서는 잘못된 토큰을 400으로 반환하는 경로도 있다. 인증 헤더 누락은 사용 중인 인증 미들웨어의 기본 응답을 따른다. 모든 인증 오류를 하나의 401 응답으로 가정하지 않는다. 기존 HTTP 오류 본문은 일반적으로 `detail`이며, 422 요청 검증은 오류 목록이 될 수 있다. 성공 응답의 `data` envelope와 동일하다고 가정하지 않는다.

## 7. 리뷰에서 보완한 안전장치

- 챌린지 서비스의 날짜 생성·미래 날짜 판정·사이클 계산과 일일 기록 화면의 날짜 기준을 `Asia/Seoul`로 맞췄다. 전체 서비스의 모든 날짜 로직이 변경되었다는 의미는 아니다.
- 사진 분석 전뿐 아니라 결과 저장 직전에도 동의, 최신 이용 대상 확인, 미확인 의료기관 안내, 사이클 상태·날짜를 재확인한다. 분석 대기 중 중단된 사이클에 결과를 뒤늦게 저장하지 않도록 했다.
- 저장 트랜잭션에서 선택 항목·사이클 행을 잠그고 기존 승인 기록을 다시 조회한다. 동시 제출의 늦은 거절 결과가 먼저 승인된 기록을 덮어쓰지 않도록 했다. 실제 DB별 동시성 검증은 별도 확인 대상이다.
- 사진 판정의 boolean·숫자 범위를 엄격히 검사하며 provider 설정뿐 아니라 실제 provider 및 결과 종류를 확인한다. 실패를 성공으로 대체하지 않는다.
- 현재 API에 연결되지 않은 기존 일반 인증·식사 사진 인증 서비스 메서드에도 V3 거절 검사를 추가했다. 향후 해당 메서드가 다시 연결되어도 V3 사진·목표 검사를 우회하지 않도록 하는 방어다.
- 후보·후속 안내 조회에는 계정과 요청 번호 검사를 적용해 계정 변경 전의 늦은 응답이 새 화면을 덮어쓰지 않도록 했다. 사진 제출 응답도 계정·사이클이 달라졌으면 이전 완료 상태를 새 화면에 적용하지 않는다.

## 8. 검증 상태와 팀 확인 사항

로컬 검증: 신규 Python 테스트 62개를 포함한 관련 회귀 테스트 69개 통과, 프론트 Node 계약 테스트 61개 통과. 저장소 전체 Ruff 검사 통과, `app`·`ai_worker` 및 신규 Python 테스트의 포맷 확인 통과. 전체 포맷 검사에서는 이번 변경과 무관한 기존 7개 파일이 지적되어 수정하지 않았다. 브라우저에서 1440px·390px 후보 표시/선호 변경/새로고침/가로 넘침을 확인했고, 별도 메모리 DB 계정으로 2유형 사진 업로드와 3유형 체크 후 기록 재조회를 확인했다. 실제 외부 Vision 호출·사진 판별 정확도와 실제 MySQL 잠금은 검증하지 않았다. 최종 원격 CI 상태는 PR에서 확인한다.

재현 테스트: `tests/test_challenge_v3_api.py`, `tests/test_challenge_v3_catalog.py`, `tests/frontend/challenge_v3.test.cjs`, `tests/frontend/challenge_v3_qa.cjs`. 브라우저 테스트는 **폐기 가능한 로컬 DB**에서만 `QA_DISPOSABLE_DB=true`를 명시해 실행한다. 실제 사용자·의료 데이터는 테스트에 사용하지 않는다.

- 선호·난이도별 3영역 구성, 중복·혼합 ID 거절, 기존 사이클·기록 유지
- 사진형 PUT 우회 차단, 개발용 mock 차단, 잘못된 boolean·confidence·파일 거절
- 승인 후 재제출 불변성, 동시 제출, 검토 도중 동의 철회·이용 대상 변경·사이클 중단
- 서울 자정 경계의 저장·재조회, 계정 변경 중 늦은 응답, 실패·재시도 화면
- 실제 DB에서의 잠금 동작과 실제 외부 이미지 provider 연결·오류 처리
- 공식 출처 링크의 접속 상태와 안전 문구 검토, 외부 사진 처리 정책·고지·동의 확정
- 밭·당근 보상의 지급 조건·중복 방지·기존 게임과의 연결 방식 확정 후 별도 범위로 구현

팀 공유 시에는 “의료 효과가 검증된 개인 맞춤 챌린지”가 아니라 “공식 자료의 일반 원칙을 바탕으로 만든, 선호·실천 단계별 3영역 챌린지”로 설명한다.
