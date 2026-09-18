# 오늘이·내일이 최종 서비스 API 계약

문서 버전: `2.0`
최종 개정일: 2026-09-17
상태: 오늘이 v3·내일이 v2 서비스 연동 최종 계약

배포 승인: 2026-09-17 두 모델 모두 위험 선별·건강교육 범위에서 `approved`이며,
버전·Artifact SHA-256·임계값이 모두 일치할 때만 사용자 범주를 공개한다. 내일이의
점수는 확률 보정을 완료한 개인 발병확률이 아니므로 퍼센트 확률로 표시하지 않는다.

이 문서는 기존 오늘이 v1 전달 계약을 대체한다. 오늘이 모델 파일명·Manifest·응답의
`model_version`은 오늘이 `knhanes-today14-sk180-service-v3`, 내일이
`rf25-tuned-education4-v2`를 사용한다.

두 결과는 진단·처방이 아니라 위험 선별과 건강교육용이다. 오늘이는 현재 조사시점의
당뇨 관련 신호를, 내일이는 다음 약 2년 조사시점까지의 신규 의사진단 위험 신호를
서로 독립적으로 반환한다.

### 공통 교육 수준 계약

- 응답함: `code_1`, `code_2`, `code_3`, `code_4` 중 하나
- 모름·무응답·미입력: JSON `null`
- 공통 API에서 `code_97` 전송 금지
- 두 모델 모두 `code_1`~`code_4` 외 값은 결측으로 변환한다.

## 1. 확정 모델

| 구분 | 오늘이 | 내일이 |
|---|---|---|
| 모델 버전 | `knhanes-today14-sk180-service-v3` | `rf25-tuned-education4-v2` |
| 모델 특성 | KNHANES 14개 | KLoSA RF25, 필수 14개 |
| Artifact | `models/artifacts/candidates/diabetes_current_screening/knhanes-today14-sk180-service-v3/model.joblib` | `models/artifacts/candidates/diabetes_incidence/rf25-tuned-education4-v2/model.joblib` |
| SHA-256 | `2189257587690adfcdf74702f69b516c0a8559cef6059ebd90d003e008c079b1` | `45f7de434a887b82aaff86a3b6afd8e99f75ebdc8bb3c0cd320484db9b71ad8e` |
| 적용 연령 | 만 19~120세 | 만 45~105세 |
| 출력 의미 | 현재 당뇨 관련 선별 신호 | 다음 인접 조사까지 신규 진단 선별 점수 |
| 결측 처리 | 수치형 Train 중앙값+indicator, 범주형 Train 최빈값+변수별 indicator, 허리둘레 전용 추정기 | 수치형 Train 중앙값+indicator, 범주형 Train 최빈값 대치 후 원-핫 인코딩(범주형 indicator 없음) |

내일이는 범주형 indicator를 추가한 v3 실험에서 Test Recall이 같고 Specificity가
`0.4027`에서 `0.3966`으로 낮아졌으므로 기존 `rf25-tuned-education4-v2`를 최종 선택한다.
여기서 “indicator 없음”은 **범주형 결측 indicator 없음**을 뜻한다. 현재 v2의 선택
수치형 결측 indicator는 유지한다.

## 2. 공통 외부 입력

| API 필드 | 형식·범위 | 원자료와 변환 | 필수 모델 |
|---|---|---|---|
| `birth_date` | `YYYY-MM-DD` | 조사일 기준 만 나이 계산 · 미래 날짜 거부 | 오늘이·내일이 |
| `sex` | `male`, `female` | KNHANES `sex`: 남 1·여 2 · KLoSA `gender1`: 남 1·여 5 · 모델별 코드로 내부 변환 | 오늘이·내일이 |
| `height_cm` | number, 120~220 cm | KNHANES `HE_ht` · KLoSA `C107` · BMI 계산에 사용 | 오늘이·내일이 |
| `weight_kg` | number, 25~250 kg | KNHANES `HE_wt` · KLoSA `C105` · BMI 계산에 사용 | 오늘이·내일이 |
| `smoking_status` | `never`, `former`, `current` | 공통 설문은 3단계 흡연 상태로 수집하며 모델별 변환은 아래 표를 따름 | 오늘이·내일이 |
| `previously_diagnosed_diabetes` | boolean | 모델 입력 특성이 아닌 대상자 제외 안전 게이트 · `true`이면 두 모델 모두 추론 거부 | 오늘이·내일이 |

`smoking_status`는 두 모델의 원자료 정의가 다르므로 같은 값을 그대로 복사하지 않는다.
사용자에게는 비흡연·과거흡연·현재흡연의 세 선택지를 제공하고 서버에서 다음과 같이 변환한다.

| API 입력 | 사용자 응답 | 오늘이14 `current_smoker` | 내일이 RF25 `smoking_status` |
|---|---|---:|---|
| `never` | 평생 비흡연 | `0` — 현재 비흡연 | `never` — 비흡연 범주 유지 |
| `former` | 과거 흡연, 현재 금연 | `0` — 현재 비흡연 | `former` — 과거흡연 범주 유지 |
| `current` | 현재 흡연 | `1` — 현재 흡연 | `current` — 현재흡연 범주 유지 |

오늘이는 KNHANES의 현재 흡연 여부에 맞춰 `never`와 `former`를 같은 값으로 축약한다.
내일이는 KLoSA의 비흡연·과거흡연·현재흡연 세 범주를 구분한다. 따라서 프론트에서
흡연 여부를 boolean 하나로 받으면 내일이의 과거흡연 정보를 복원할 수 없다.

## 3. 오늘이 입력 계약

### 필수

| API 필드 | 형식·허용값 | KNHANES 원본 입력 설명 |
|---|---|---|
| 공통 6개 | 위 공통표 | 생년월일·성별·키·체중·3단계 흡연 상태·기존 진단 여부 |
| `alcohol_frequency` | 정수 `1,2,3,4,5,6,8` | 원본 `BD1_11`: 최근 1년 음주빈도 · `1`: 최근 1년간 전혀 마시지 않음 · `2`: 월 1회 미만 · `3`: 월 1회 정도 · `4`: 월 2~4회 · `5`: 주 2~3회 · `6`: 주 4회 이상 · `8`: 비해당(평생 음주 경험 없음) · 이외 코드와 미응답·`null`은 허용하지 않음 |

### 선택

| API 필드 | 형식·범위 | KNHANES 원본 입력 설명 | 미입력 처리 |
|---|---|---|---|
| `education_level` | `code_1`~`code_4`, null | KNHANES `edu` · `code_1`: 초졸 이하 · `code_2`: 중졸 · `code_3`: 고졸 · `code_4`: 대졸 이상 · 그 외 값은 결측 | Train 최빈값 대치 + 결측 indicator |
| `waist_cm` | number/null, 40~200 cm | `HE_wc`, 허리둘레 실측 | 키·체중·나이·성별 기반 Train 전용 추정기 |
| `systolic_bp` | number/null, 50~300 mmHg | `HE_sbp`, 반복 측정 후 제공된 수축기혈압 | Train 중앙값+결측 indicator |
| `diastolic_bp` | number/null, 30~200 mmHg | `HE_dbp`, 반복 측정 후 제공된 이완기혈압 | Train 중앙값+결측 indicator |
| `region` | integer/null, 1~17 | 원본 `region` · `1` 서울 · `2` 부산 · `3` 대구 · `4` 인천 · `5` 광주 · `6` 대전 · `7` 울산 · `8` 세종 · `9` 경기 · `10` 강원 · `11` 충북 · `12` 충남 · `13` 전북 · `14` 전남 · `15` 경북 · `16` 경남 · `17` 제주 | Train 최빈값(현재 9·경기) 대치 + 지역 결측 indicator |
| `diabetes_family_history` | boolean/null | 원본 `HE_DMfh1~3` · 부·모·형제자매 중 당뇨 의사진단 한 명 이상 | Train 최빈값 대치 + 결측 indicator · `null`을 `false`로 바꾸지 않음 |
| `hypertension_family_history` | boolean/null | 원본 `HE_HPfh1~3` · 부·모·형제자매 중 고혈압 의사진단 한 명 이상 | Train 최빈값 대치 + 결측 indicator · `null`을 `false`로 바꾸지 않음 |

오늘이 모델 내부 순서는 `age,height_cm,weight_kg,waist_cm,bmi,systolic_bp,
diastolic_bp,sex,current_smoker,education,region,diabetes_family_history,
hypertension_family_history,alcohol_frequency`로 고정한다. BMI는 서버가
`weight_kg/(height_cm/100)^2`로 계산한다.
수축기·이완기 혈압을 둘 다 입력하면 `systolic_bp > diastolic_bp`여야 한다.
한쪽만 입력한 경우 입력된 값은 검증하고 나머지는 결측 처리한다.

### 오늘이 요청 예시

```json
{
  "birth_date": "1966-01-01",
  "sex": "male",
  "height_cm": 170,
  "weight_kg": 70,
  "smoking_status": "former",
  "education_level": "code_3",
  "alcohol_frequency": 2,
  "previously_diagnosed_diabetes": false,
  "waist_cm": 85,
  "systolic_bp": null,
  "diastolic_bp": null,
  "region": 1,
  "diabetes_family_history": null,
  "hypertension_family_history": false
}
```

## 4. 내일이 입력 계약

공통 요청의 `tomorrow` 객체에 아래 필드를 넣는다. 필수 모델 특성은 14개이며,
나이·BMI 파생용 입력과 대상자 제외 게이트를 포함한 필수 API 필드는 16개다.
`age`, `bmi`, `log_household_income`은 서버에서 계산하므로 직접 전송하지 않는다.
원본 조사 코드는 아래 API 값으로 변환한다.

### 필수 입력 — API 16개 / 모델 특성 14개

필수값 누락·`null`은 대치하지 않고 오류로 처리한다.

| API 필드 → 모델 특성 | JSON 자료형·단위·허용값 | KLoSA 원자료 의미·입력 예시·처리 |
|---|---|---|
| `birth_date` → `age` | string, `YYYY-MM-DD` | 원본 `A002_age`: 기저 조사 만 나이 · 입력 예: `"1966-01-01"` · 분석 기준일 기준 만 45~105세 · 미래 날짜 불가 |
| `sex` | string, `male` / `female` | 원본 `gender1`: 남 1 · 여 5 · 입력 예: `"female"` · 원본 숫자 1·5를 직접 보내지 않음 |
| `height_cm` → `bmi` | number, 120~220 cm | 원본 `C107`: 키 · 입력 예: `170.5` · 미터 단위나 `"170cm"` 문자열 불가 |
| `weight_kg` → `bmi` | number, 25~250 kg | 원본 `C105`: 체중 · 입력 예: `70.2` · 키와 함께 BMI=`kg/(cm/100)^2` 계산 · 파생 BMI 허용 범위 10~70 kg/m² · 키·체중은 하나의 BMI 특성으로 통합 |
| `smoking_status` | string, `never` / `former` / `current` | 원본 `smoke`: 0 비흡연 · 1 과거흡연 · 2 현재흡연 · 입력 예: `"former"` · 세 범주를 유지 |
| `current_drinker` | boolean | 1차 원본 `Alc`, 이후 원본 `alc` · 1 현재음주→`true` · 2 과거음주·3 비음주→`false` · 음주빈도 숫자와 구별 |
| `regular_exercise` | boolean | 원본 `C108` · 1 규칙적 운동→`true` · 5 아니오→`false` · `true`이면 운동일·시간 모두 양수 · `false`이면 모두 0 |
| `exercise_days_per_week` | number, 0~7 일/주 | 원본 `C111`: 운동 빈도 · 입력 예: `3` = 주 3일 · 화면은 정수 선택 권장, 코어는 소수도 허용 · 비운동자는 0 |
| `exercise_minutes` | number, 0~720 분/회 | 원본 `C112`: 운동시간 · 입력 예: `40` = 회당 40분 · 주간 총량이나 시간 단위가 아님 · 비운동자는 0 |
| `hypertension_diagnosis` | boolean | 원본 `chronic_a`: 고혈압 의사진단 · 1 있음→`true` · 5 없음→`false` |
| `heart_disease_diagnosis` | boolean | 원본 `chronic_f`: 심장질환 의사진단 · 1 있음→`true` · 5 없음→`false` |
| `arthritis_rheumatism_diagnosis` | boolean | 원본 `chronic_i`: 관절염·류마티스 의사진단 · 1 있음→`true` · 5 없음→`false` |
| `marital_status` | string, `code_1`~`code_5` | 원본 `marital` · `code_1` 혼인중 · `code_2` 별거 · `code_3` 이혼 · `code_4` 사별 또는 실종(이산가족) · `code_5` 결혼한 적 없음 · 입력 예: `"code_1"` · 숫자·자유 문장 불가 |
| `depressed_feeling_last_week` | string, `code_1`~`code_4` | 원본 `C144`: 지난 일주일 우울감 · `code_1` 잠깐 또는 없음(하루 미만) · `code_2` 가끔(1~2일) · `code_3` 자주(3~4일) · `code_4` 항상(5~7일) · 입력 예: `"code_2"` · 우울증 진단 여부와 별도이며 연속 점수로 보내지 않음 |
| `sleep_difficulty_last_week` | string, `code_1`~`code_4` | 원본 `C148`: 지난 일주일 잠을 잘 이루지 못함 · `code_1` 잠깐 또는 없음(하루 미만) · `code_2` 가끔(1~2일) · `code_3` 자주(3~4일) · `code_4` 항상(5~7일) · 입력 예: `"code_2"` · 수면시간 숫자와 구별 |
| `previously_diagnosed_diabetes` → 대상자 제외 게이트 | boolean | `false`일 때 추론 대상 · `true`이면 기존 진단자로 추론에서 제외 · 모델의 25개 특성에는 포함하지 않음 |

### 선택 입력 — API·모델 특성 11개

선택값은 생략 또는 JSON `null`로 전달한다. 교육 수준의 모름·무응답은 공통
API에서 명시적으로 `null`을 보낸다. 결측 대치는 Train에서 학습한 전처리기를 사용한다.

| API 필드 → 모델 특성 | JSON 자료형·단위·허용값 | KLoSA 원자료 의미·입력 예시·결측 처리 |
|---|---|---|
| `cancer_diagnosis` | boolean / null | 원본 `chronic_c`: 암 의사진단 · 1 있음→`true` · 5 없음→`false` · 모름·미입력→`null` · 결측은 Train 최빈값 |
| `chronic_lung_disease_diagnosis` | boolean / null | 원본 `chronic_d`: 만성 폐질환 의사진단 · 1 있음→`true` · 5 없음→`false` · 입력 예: `false` · 결측은 Train 최빈값 |
| `liver_disease_diagnosis` | boolean / null | 원본 `chronic_e`: 간질환 의사진단 · 1 있음→`true` · 5 없음→`false` · 입력 예: `null` · 결측은 Train 최빈값 |
| `cerebrovascular_disease_diagnosis` | boolean / null | 원본 `chronic_g`: 뇌혈관질환 의사진단 · 1 있음→`true` · 5 없음→`false` · 입력 예: `false` · 결측은 Train 최빈값 |
| `psychiatric_disease_diagnosis` | boolean / null | 원본 `chronic_h`: 정신과 질환 의사진단 · 최근 우울감 설문과 별도 · 1 있음→`true` · 5 없음→`false` · 입력 예: `null` · 결측은 Train 최빈값 |
| `annual_household_income_10k_krw` → `log_household_income` | number / null, 0~123500 만원/년 | 원본 `hhinc`: 연간 가구소득 · 연 3,000만원 입력 예: `3000` · 월소득·원 단위·로그값을 보내지 않음 · 서버에서 `log1p` 변환 · 결측은 Train 중앙값+indicator |
| `education_level` | string / null, `code_1`~`code_4` | 원본 `edu` · `code_1` 초졸 이하 · `code_2` 중졸 · `code_3` 고졸 · `code_4` 대졸 이상 · 모름·무응답·그 외 값은 결측 · 결측은 Train 최빈값 |
| `household_structure` | string / null, `single_person` / `multi_person` | 원본 `hhsize` · 1명→`"single_person"` · 2명 이상→`"multi_person"` · 가구원 수 숫자는 보내지 않음 · 결측은 Train 최빈값 |
| `health_satisfaction_score` | number / null, 0~100점 | 원본 `G026`: 건강상태 만족도 · 입력 예: `70` · 5단계 주관적 건강상태 응답과 별도 · 결측은 Train 중앙값+indicator |
| `economic_satisfaction_score` | number / null, 0~100점 | 원본 `G027`: 경제상태 만족도 · 입력 예: `60` · 결측은 Train 중앙값+indicator |
| `overall_quality_of_life_score` | number / null, 0~100점 | 원본 `G030`: 전반적 삶의 질 만족도 · 입력 예: `80` · 결측은 Train 중앙값+indicator |

#### 누락·자료형·변환 규칙

- 선택값은 키 생략 또는 JSON `null`로 보낸다. `"null"`, `""`, `"모름"`, 숫자 `-9`를 결측 표시로 보내지 않는다.
- 숫자는 따옴표 없는 JSON number, 여부는 따옴표 없는 `true`/`false`로 보낸다. `"false"`, `0`, `1`은 boolean 입력의 대체값이 아니다.
- 필수값의 누락·`null`은 오류다. 필수 진단력에 모른다고 응답하면 임의로 `false`로 채우지 않는다.
- `regular_exercise=false`이면 운동일·운동시간은 모두 `0`이어야 한다. 양수가 하나라도 있으면 모순 입력으로 거부한다.
- `regular_exercise=true`이면 운동일·운동시간은 모두 `0`보다 커야 한다. 둘 중 하나라도 `0`이면 모순 입력으로 거부한다.
- 선택 수치형 결측은 Train 중앙값+결측 indicator를 적용한다. 선택 범주형 결측은 Train 최빈값으로 대치하고 별도 결측 indicator를 추가하지 않는다. 소득은 유효값에 `log1p`를 적용한 후 입력한다.
- `0`은 소득·만족도 등의 유효 응답이다. 미입력으로 치환하지 않는다. 선택 진단력의 `null`도 `false`로 바꾸지 않는다.
- 교육 수준은 두 모델 모두 `code_1`~`code_4`만 유효하다. 모름·무응답은 `null`로
  보내며 `code_97`을 포함한 나머지 값은 결측 처리한다.
- 알 수 없는 필드명은 거부한다. 필수값만 보낼 때에도 모델 내부는 선택 특성 11개를 결측으로 채운 고정 25열 순서를 유지한다.

#### 필수값만 포함한 내일이 입력 예시

```json
{
  "birth_date": "1966-01-01",
  "sex": "male",
  "height_cm": 170,
  "weight_kg": 70,
  "smoking_status": "former",
  "current_drinker": true,
  "regular_exercise": true,
  "exercise_days_per_week": 3,
  "exercise_minutes": 40,
  "hypertension_diagnosis": false,
  "heart_disease_diagnosis": false,
  "arthritis_rheumatism_diagnosis": false,
  "marital_status": "code_1",
  "depressed_feeling_last_week": "code_4",
  "sleep_difficulty_last_week": "code_4",
  "previously_diagnosed_diabetes": false
}
```

추론 코어의 검증 오류는 `ValueError`이며, HTTP `422 REQUIRED_INPUT_MISSING` 등의
응답으로 변환하는 것은 백엔드의 책임이다.

### 내일이 위험 경계

- `low`: 점수 `< 0.01772772727901335`
- `moderate`: `0.01772772727901335 <= 점수 < 0.02113653615781283`
- `high`: 점수 `>= 0.02113653615781283`

내부 모델과 공개 API 모두 중간 위험 범주를 `moderate`로 사용한다. RF 점수는 보정된
개인 발병확률이 아니므로 프론트에서 백분율 확률로 표시하지 않는다.

## 5. 공통 응답

```json
{
  "today": {
    "status": "succeeded",
    "screening_score": 0.0312,
    "signal_detected": true,
    "decision_threshold": 0.022445685526736606,
    "model_version": "knhanes-today14-sk180-service-v3",
    "threshold_version": "today14-missing-indicator-validation-spec042-v2"
  },
  "tomorrow": {
    "status": "succeeded",
    "screening_score": 0.0231,
    "risk_category": "high",
    "thresholds": {
      "moderate": 0.01772772727901335,
      "high": 0.02113653615781283
    },
    "model_version": "rf25-tuned-education4-v2",
    "threshold_version": "education4-validation-spec043-moderate-recall090-v2"
  },
  "disclaimer": "위 결과는 진단·처방이 아닌 위험 선별과 건강교육 정보입니다."
}
```

오늘이와 내일이는 서로 다른 과제이므로 결과가 달라도 오류가 아니다. 오늘이 신호가
높고 내일이가 낮으면 현재 상태 확인을 우선 안내하고, 오늘이가 낮고 내일이가 높으면
장기 생활관리와 정기검진을 안내한다. 약물 변경을 권고하지 않는다.

## 6. 오류와 부분 성공

| 상태 | HTTP/코드 | 처리 |
|---|---|---|
| 필수값 누락 | 422 `REQUIRED_INPUT_MISSING` | 해당 모델만 실패, 다른 모델 성공 결과 유지 |
| 범위·코드 오류 | 422 `INPUT_OUT_OF_RANGE` | 필드별 사유 반환 |
| 지원 연령 밖 | 422 `UNSUPPORTED_AGE` | 모델별 적용 연령을 함께 반환 |
| Artifact 없음 | 503 `MODEL_ARTIFACT_UNAVAILABLE` | 실제 결과처럼 임의 점수 표시 금지 |
| 해시 불일치 | 503 `MODEL_ARTIFACT_INTEGRITY_ERROR` | 로딩 중단 |
| 일부 모델 실패 | 200 또는 207 | 성공 모델 결과 유지, 실패 모델은 `status=failed` |

## 7. 서비스 입력에서 제거한 변수

최종 두 모델이 사용하지 않는 다음 필드는 오늘이·내일이 추론 요청과 설문에서
제거한다: `walking_days`, `energy_kcal`, `protein_g`, `fat_g`,
`carbohydrate_g`, `sodium_mg`, `urban`, `income_quartile`,
`household_income_quartile`, `aerobic_activity`, `fasting_glucose`, `hba1c`.

공복혈당·당화혈색소·기존 진단·약물 정보는 특히 현재 당뇨 라벨을 직접 구성하거나
노출할 수 있으므로 모델 특성에 넣지 않는다. 과거 실험 재현을 위한 오프라인 데이터
전처리 열은 삭제하지 않지만 공개 API와 사용자 설문에서는 받지 않는다.
