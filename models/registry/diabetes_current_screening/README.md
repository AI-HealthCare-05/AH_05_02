# 당뇨병 현재 위험 신호 선별 모델 레지스트리

이 디렉터리는 KNHANES 기반 `오늘이` 모델만 관리한다. KLoSA 기반 `내일이` 미래발병 모델은
`models/registry/diabetes_incidence/`에서 별도로 관리한다.

- `model_key`: `diabetes_current_screening`
- 목적: 미진단 성인의 현재 당뇨 관련 임상 신호 선별
- 금지 표현: 진단, 확진, 미래 발병확률, 치료·복약 필요성
- 점수 결합 금지: `diabetes_incidence` 점수와 평균·합산하지 않는다.
- 실제 `.joblib` 파일은 Git에 올리지 않고 SHA-256이 일치하는 로컬 아티팩트만 사용한다.

`v0.5.0`은 비교 기준 Champion이지만 운영 승인은 아직 받지 않았다. `v0.6.1`은 Test Recall이
개선된 Challenger이며 추가 외부 검증 전에는 운영 모델로 승격하지 않는다.
