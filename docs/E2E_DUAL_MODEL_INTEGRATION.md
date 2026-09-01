# 오늘이·내일이 웹서비스 통합 계약

## 연결 흐름

`회원가입·동의 → 적합성 확인 → 건강정보 저장 → 오늘이 → 내일이(45세 이상) → 결과 → 챌린지 → 대시보드 → 당근의 숲`

| 구분 | 오늘이 | 내일이 |
| --- | --- | --- |
| 모델 키 | `diabetes_current_screening` | `diabetes_incidence` |
| 데이터 | KNHANES | KLoSA |
| 대상 | 만 19세 이상 미진단 성인 | 만 45세 이상 미래예측 적합 사용자 |
| 의미 | 현재 당뇨 관련 위험 신호 선별 | 약 2년 후 신규 당뇨 발병 위험 선별 |
| 출력 유형 | `current_screening` | `future_incidence` |
| 금지 | 진단·처방, 미래확률 해석 | 진단·처방, 확정적 미래 표현 |

두 모델의 점수는 모집단·라벨·관측시점이 다르므로 합산하거나 변화율로 비교하지 않는다.

## API

두 모델 모두 `POST /api/v1/prediction-jobs`를 사용하고 `model_key`로 구분한다.

```json
{
  "checkup_id": 1,
  "model_key": "diabetes_current_screening"
}
```

```json
{
  "checkup_id": 1,
  "model_key": "diabetes_incidence"
}
```

상태 조회는 `GET /api/v1/prediction-jobs/{job_id}`, 결과 조회는
`GET /api/v1/predictions/{prediction_id}`를 공통으로 사용한다.

## 공개 정책

- 모델 바이너리는 저장소에 커밋하지 않고 배포 환경에 별도 공급한다.
- 운영 승인 전에는 개인별 위험 범주·확률·선별 판정을 화면에 표시하지 않는다.
- `DEMO_MODE=true`는 API·DB·프론트 연결만 검증하고 개인 판정값을 생성하지 않는다.
- 기진단자와 긴급 경고 증상 사용자는 모델 실행보다 의료기관 안내를 우선한다.
- 챌린지와 당근의 숲은 치료·복약 기능이 아닌 일반 건강생활 실천 기능으로 유지한다.

## 프론트 동작

- 만 19~44세: 오늘이만 요청하고 현재 위험 신호 영역을 표시한다.
- 만 45세 이상: 오늘이를 먼저 요청한 뒤 내일이를 별도로 요청한다.
- 내일이 결과의 `prediction_id`를 챌린지 추천과 대시보드 연결에 사용한다.
- 내일이 실행 대상이 아니면 오늘이 결과의 `prediction_id`를 후속 건강생활 흐름에 사용한다.
