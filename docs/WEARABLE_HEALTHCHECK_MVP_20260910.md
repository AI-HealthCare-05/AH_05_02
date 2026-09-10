# 웨어러블·건강검진 입력 MVP

## 구현 범위

이 MVP는 제조사 계정에 직접 로그인하지 않는다. Apple 건강 앱의 `export.xml` 또는 Android Health Connect의
내보내기 JSON을 로컬에서 일별 요약으로 정제한 뒤, 사용자가 확인한 값만 API에 전송한다.

| 입력 | MVP 처리 | 서비스 활용 |
| --- | --- | --- |
| Apple Health XML | 걸음·운동 시간·수면·안정시 심박 일별 집계 | 건강정보 입력 후보, 운동 챌린지 인증 후보 |
| Android Health Connect JSON | 걸음·운동 시간·수면·안정시 심박 일별 집계 | 건강정보 입력 후보, 운동 챌린지 인증 후보 |
| 2025 일반건강검진 결과통보서 OCR 텍스트 | 검진일·신체계측·혈압·혈액검사 수치 초안 추출 | 사용자가 원문과 대조한 뒤 입력 화면에 반영 |

원본 파일, 이름, 주민등록번호, 앱 패키지명, 기기 식별자는 서버에 올리지 않는다. 정제 결과도 자동으로 건강검진
기록을 덮어쓰지 않으며 사용자 확인을 요구한다.

## 실행 예시

### Apple Health

```python
from src.wearables.apple_health import build_daily_summaries, flag_duplicates, iter_normalized_records
from src.wearables.common import from_apple_daily_summary

records = flag_duplicates(iter_normalized_records("export.xml", user_pseudo_id="local-user"))
items = [from_apple_daily_summary(item).as_api_item() for item in build_daily_summaries(records)]
```

### Android Health Connect

```python
from src.wearables.android_health import parse_health_connect_export

items = [item.as_api_item() for item in parse_health_connect_export("health-connect.json")]
```

정제된 `items`는 `POST /api/v1/wearables/daily-summaries/import`에 전달한다. 응답의
`exercise_verification_candidates`는 기준 충족 여부와 근거를 보여준다. 실제 챌린지 자동 기록은 활성 사이클의
`activity_check`에만 적용한다.

최근 7일 건강정보 후보는 다음 API로 확인한다.

```text
GET /api/v1/wearables/health-candidates?start_date=2026-09-01&end_date=2026-09-07
```

`exercise_days_per_week`, `exercise_minutes`, `regular_exercise`는 입력 후보이며 사용자가 확인해야 한다.

### 2025 건강검진 결과 추출 예시

공식 빈 서식: `docs/reference/forms/2025_general_health_checkup_result_form.pdf`

개인정보가 없는 합성 OCR 예시: `docs/samples/health_checkup/2025_general_health_checkup_synthetic_ocr.txt`

```json
{
  "document_name": "2025_general_health_checkup_sample.txt",
  "ocr_text": "검진일: 2025-06-18\\n신장: 168.2 cm\\n체중: 72.4 kg\\n혈압: 132 / 84 mmHg\\n공복혈당: 108 mg/dL"
}
```

위 요청을 `POST /api/v1/ocr-drafts`에 보내면 확인 전 초안만 반환한다. 이름과 주민등록번호는 추출·저장하지 않는다.

## 판정 원칙

- 운동 인증 후보: 일일 활동 10분 이상 또는 1,000걸음 이상인 경우. 이는 MVP 챌린지 완료 기준이며 운동 효과나
  질병 위험 감소 판정이 아니다.
- 규칙적 운동 후보: 확인된 7일 기록에서 활동일 3일 이상이면서 총 활동 150분 이상인 경우. 설문 입력을 돕는
  후보값일 뿐이며 자동 저장하지 않는다.
- 누락·미착용 의심·중복 기록은 검토 대상으로 표시한다.

## 공식 서식 출처

- 국가법령정보센터. 건강검진 실시기준 [별지 제6호서식] 일반건강검진 결과통보서
  (2025. 1. 1. 개정).
  <https://www.law.go.kr/LSW/flDownload.do?bylClsCd=200203&flNm=%5B%EB%B3%84%EC%A7%80+6%5D+%EC%9D%BC%EB%B0%98%EA%B1%B4%EA%B0%95%EA%B2%80%EC%A7%84+%EA%B2%B0%EA%B3%BC%ED%86%B5%EB%B3%B4%EC%84%9C&flSeq=148392279>
