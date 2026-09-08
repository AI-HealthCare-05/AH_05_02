# 모델링 공통 코드

데이터 분리, 공통 특성 계약, 모델 생성기와 임계값 선택처럼 여러 실험이 공유하는 코드만 둡니다.

- `knhanes_current_screening.py`: KNHANES 미진단 성인의 현재 당뇨 임상 신호를 Recall 중심으로 선별하는 별도 보조 모델입니다. KLoSA 미래 신규발병 모델과 확률을 직접 합치지 않습니다.
- `knhanes_team1_six_feature_benchmark.py`: 1조 공개 6개 입력·LR/RF·Platt 방법을 우리 미진단 코호트와 시간 분할에서 독립 재현하는 비교 실험입니다.
- `transformers.py`: 실측 허리둘레를 보존하면서 결측일 때만 키·체중 중심 신체계측 모델로 보완하는 직렬화 가능한 변환기입니다.
- `klosa_discrete_time_hazard.py`: KLoSA long panel을 person-period로 변환하고 Logistic·RF·LightGBM으로 약 2년 구간별 신규 당뇨 진단 위험과 누적 위험 신호곡선을 실험하는 템플릿입니다.
특정 실험의 조건과 결과는 `experiments/`에 둡니다.
