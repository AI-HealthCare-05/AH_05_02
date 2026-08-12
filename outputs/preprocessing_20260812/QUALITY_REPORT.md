# KLoSA·KNHANES 전처리 품질보고서

생성 기준일: 2026-08-12

## 처리 결과

- KNHANES: 67,019건, 2016–2024년
- KLoSA: 74,834개 패널 관측행, 1–10차
- 중복 키: KNHANES `연도:ID`, KLoSA `PID-차수` 기준 0건
- 두 조사는 행 단위로 합치지 않고 공통 개념의 통합 변수 명세로 연결함

## 모델별 분석 표본

| dataset   | target_definition   | disease      | age_group         |   rows |   positive | prevalence   |   train_rows |   validation_rows |   test_rows |
|:----------|:--------------------|:-------------|:------------------|-------:|-----------:|:-------------|-------------:|------------------:|------------:|
| KNHANES   | undiagnosed         | hypertension | 19+               |  38905 |       4333 | 11.14%       |        22834 |              7702 |        8369 |
| KNHANES   | undiagnosed         | hypertension | 40+               |  25737 |       3662 | 14.23%       |        14699 |              5218 |        5820 |
| KNHANES   | undiagnosed         | hypertension | 65+               |   6709 |       1308 | 19.50%       |         3580 |              1457 |        1672 |
| KLoSA     | incident            | hypertension | survey_population |  38235 |       2315 | 6.05%        |        26768 |              5722 |        5745 |
| KNHANES   | undiagnosed         | diabetes     | 19+               |  44828 |       1945 | 4.34%        |        26005 |              9132 |        9691 |
| KNHANES   | undiagnosed         | diabetes     | 40+               |  32089 |       1788 | 5.57%        |        18160 |              6680 |        7249 |
| KNHANES   | undiagnosed         | diabetes     | 65+               |  10774 |        761 | 7.06%        |         5716 |              2427 |        2631 |
| KLoSA     | incident            | diabetes     | survey_population |  51807 |       1299 | 2.51%        |        36273 |              7678 |        7856 |

## 핵심 전처리 원칙

- KNHANES는 현재 검사·설문 기반의 임상 위험 선별 타깃이다.
- KLoSA는 미진단 이력이 확인되고 인접한 다음 차수 응답이 있는 사람의 약 2년 신규 진단 타깃이다.
- 혈압, 공복혈당, HbA1c, 진단·복약 변수는 타깃 구성 또는 적합성 확인에만 사용하고 모델 입력에서 제외했다.
- KNHANES는 연도 기준 train(2016–2020), validation(2021–2022), test(2023–2024)로 분리했다.
- KLoSA는 동일 PID가 한 split에만 들어가도록 그룹 해시 분리했다.
- 결측치 대치·스케일링·범주 인코딩은 이 파일 생성 단계에서 학습하지 않는다. 향후 각 모델의 train split에서만 적합한다.
- KLoSA는 모집 특성을 반영해 연령별로 나누지 않고 하나의 패널 모델만 구성한다.

## 해석 제한

예측 결과는 의료 진단이나 처방이 아니라 위험 선별과 건강교육 목적으로만 사용한다. KNHANES와 KLoSA는 조사설계·관측단위·타깃 시점이 달라 행 단위 결합이나 성능의 단순 비교를 금지한다.
