# Apple Health → 공통 웨어러블 스키마 대응표

`src/wearables/apple_health.py`가 Apple `export.xml`을 파싱해서 팀 공통 출력 스키마(체크리스트의 "웨어러블 공통 출력 기준")로 변환하는 규칙을 정리한 문서다. 파서 구현/테스트와 1:1로 대응하며, 실제 사용자 1.2GB export.xml(레코드 1,355,359건, 2019-10-25~2026-08-24)로 파싱·중복처리·일별 집계까지 전 구간을 검증했다 (개인 식별 가능한 원본 값은 어떤 단계에서도 화면 출력·파일 저장하지 않음).

## 1. 공통 컬럼 대응표

| 공통 컬럼 | Apple 원본 소스 | 변환 규칙 |
|---|---|---|
| `user_pseudo_id` | (Apple에는 없음, 호출 시 파라미터로 주입) | 파이프라인 호출자가 넘긴 익명화 ID를 그대로 통과시킴. Apple export 파일 자체에는 사용자 식별자가 없음. |
| `platform` | (고정값) | 항상 `"apple_health"`. |
| `record_type` | `<Record type="HK...">`, `<Workout workoutActivityType="HK...">`, `<ActivitySummary>` | `RECORD_TYPE_MAP`으로 6종 매핑: `HKQuantityTypeIdentifierStepCount`→`steps`, `...DistanceWalkingRunning`→`distance`, `...ActiveEnergyBurned`→`active_energy`, `...HeartRate`→`heart_rate`, `...RestingHeartRate`→`resting_heart_rate`, `HKCategoryTypeIdentifierSleepAnalysis`→`sleep`. `<Workout>`은 `workout:{activityType 소문자}` (예: `workout:walking`, `workout:badminton`). `<ActivitySummary>`는 `activity_summary` 고정. 그 외 타입(생리주기, 여드름, 설사 등)은 파싱 대상에서 제외. |
| `start_at_utc` / `end_at_utc` | `startDate` / `endDate` (`"YYYY-MM-DD HH:MM:SS +ZZZZ"`) | `%Y-%m-%d %H:%M:%S %z`로 파싱 후 UTC로 변환(`astimezone(timezone.utc)`). `ActivitySummary`는 `dateComponents`(날짜만, 시간 없음)만 있어 자정 기준 naive datetime으로 처리. |
| `local_date` | `startDate`의 로컬 날짜 부분 | 항상 **시작 시각 기준** 현지 날짜. 자정을 넘기는 수면 기록(예: 23:40~익일 06:55)도 시작일에 귀속. |
| `timezone_offset` | `startDate`의 `+ZZZZ` 오프셋 | `"+09:00"` 형태 문자열로 정규화. |
| `value` | `<Record value="...">`, `<Workout duration="...">`, `<ActivitySummary activeEnergyBurned="...">` 등 | 수치는 float 변환. 거리(`distance`)는 `unit="mi"`이면 ×1.60934로 km 환산 후 `unit="km"`으로 통일. 수면(`sleep`)은 value 자체가 아니라 `endDate - startDate`를 분 단위로 계산해서 채움. |
| `unit` | `<Record unit="...">` 또는 파생 | 원본 unit 유지(단, 거리 mi→km 변환), 수면은 `"min"`, 운동/활동요약은 각 항목 성격에 맞는 단위(분/kcal). |
| `source_app` | `sourceName` (**원본 문자열 자체는 절대 저장/출력 안 함**) | `classify_source()`가 `sourceName`/`device` 속성을 분류만 해서 반환: Apple Watch/iPhone 접미사 → `"apple_health"`, `KNOWN_THIRD_PARTY_APPS`(예: Pillow→`pillow`)에 매칭되면 해당 코드, 그 외 → `"unknown"`. |
| `device_type` | `sourceName` (분류만) | `classify_source()` 결과: watch / phone / other. |
| `recording_method` | `<MetadataEntry key="HKWasUserEntered" value="1">` 유무, 또는 레코드 종류 | `HKWasUserEntered=1`이면 `"수동"`, 아니면 `"자동"`. `<Workout>`은 별도 트래킹 세션이므로 항상 `"능동"`. |
| `source_record_id` | `sourceName` + `record_type` + `startDate` + `endDate` + `value` | `sourceName`을 SHA-256으로 1차 해시한 뒤, 나머지 필드와 함께 다시 SHA-256 해시해서 앞 24자만 사용. **원본 `sourceName` 문자열은 어떤 산출물에도 그대로 남지 않음** (기기 이름에 실제 소유자 이름이 포함되는 경우가 실제 데이터에서 확인됨). |
| `quality_flag` | (파생값) | 아래 "2. 품질 플래그 규칙" 참고. 기본값 `"정상"`. |

## 2. 품질 플래그 규칙

- **`"결측"`**: 생리학적으로 불가능한 값(`PLAUSIBLE_RANGES` 벗어남: 심박수 25~250bpm, 안정시심박 25~150bpm, 걸음수 0~100,000, 거리 0~500km, 활동칼로리 0~20,000kcal 밖).
- **`"미착용 의심"`**: 해당 일자 걸음수가 0이거나, `ActivitySummary`의 활동칼로리가 0인 경우.
- **`"중복"`**: 같은 `record_type` 내에서 시간 구간이 겹치는 레코드 그룹(`flag_duplicates()`) 중, 우선순위가 낮은 소스(watch=0 > phone=1 > 기타=99, 동순위면 시작시각 빠른 쪽)에 부여. 최우선 소스 1건만 `"정상"`으로 남고 나머지는 전부 `"중복"`.
- **`"정상"`**: 위 조건에 해당하지 않는 기본 상태.
- 수면 값 중 `HKCategoryValueSleepAnalysisInBed`(침대에 누워있음, 실제 수면 아님)는 **레코드 자체를 생성하지 않음** (`Asleep*` 계열만 수면으로 인정).

## 3. 일 단위 요약(DailySummary) 집계 규칙

`(user_pseudo_id, local_date)` 기준으로 집계하며, `quality_flag == "중복"`인 레코드는 모든 합산에서 제외하고 대신 그 날짜에 `"중복_레코드_제외"` 플래그를 추가한다.

| 요약 필드 | 집계 방식 |
|---|---|
| `steps` | 해당일 `steps` 레코드 합산 |
| `distance_km` | 해당일 `distance` 레코드 합산(이미 km로 정규화됨) |
| `active_energy_kcal` | 해당일 `active_energy` 레코드 합산 |
| `resting_heart_rate` | 해당일 `resting_heart_rate` 레코드 평균 |
| `sleep_minutes` | 해당일(시작일 기준) `sleep` 레코드 합산 |
| `workout_minutes` / `workout_count` | 해당일 `workout:*` 레코드 시간 합산 / 건수 |
| `quality_flags` | 그 날 발생한 `"정상"`/`"중복"` 이외의 플래그(`"결측"`, `"미착용 의심"`, `"중복_레코드_제외"`)를 리스트로 누적 |

해당 일자에 데이터가 없는 필드는 `None`으로 남기고 0으로 채우지 않는다(실측 없음과 실제 0을 구분).

## 4. 스코프에서 제외한 것

- `<Me>`의 생년월일/성별/혈액형/피부타입 등 개인 특성 정보 — 파싱하지 않음(수집 대상 아님).
- 걸음수·거리·활동칼로리·심박수·안정시심박수·수면 6종 + 운동 세션(`Workout`) + 일일 활동 요약(`ActivitySummary`) 외 다른 `HK*` 타입(생리주기, 여드름, 설사, 컨디션 변화 등)은 무시.
- `sourceName` 원본 문자열, `device` 원본 문자열 — 분류된 카테고리(`source_app`/`device_type`)로만 대체, 원본은 어디에도 저장하지 않음.

## 5. 실측 검증 결과 (2026-09-09, 실제 export.xml 1.2GB)

파싱 전 구간(`iter_normalized_records` → `flag_duplicates` → `build_daily_summaries`)을 실제 데이터로 실행해 크래시 없이 완료됨. 개인 식별 가능한 실제 값은 콘솔에 출력하지 않고 집계 수치만 확인:

- 총 레코드 1,355,359건 (heart_rate 343,234 / active_energy 578,407 / distance 260,856 / steps 168,771 / resting_heart_rate 1,358 / sleep 628 / workout 330 / activity_summary 1,775)
- 품질 플래그: 정상 1,355,170 / 미착용 의심 189 (전체 파싱 기준, 결측 0건 — 실측 데이터에 생리학적으로 불가능한 값 없었음)
- 중복 처리 후 `"중복"` 플래그 233,897건 (기기 여러 대가 같은 시간대를 중복 기록한 것으로 추정)
- 일별 요약 2,495일 생성 (2019-10-25 ~ 2026-08-24)
- 전체 처리 시간 약 56초, 피크 메모리 약 1GB (스트리밍 파싱이라 파일 크기 대비 메모리 사용량은 완만함)
