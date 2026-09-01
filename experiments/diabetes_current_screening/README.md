# 오늘이: KNHANES 현재 당뇨 위험 신호 선별

| 폴더 | 지위 | 설명 |
| --- | --- | --- |
| `champion_v050/` | 비교 기준 Champion | Validation Recall이 더 높아 현재 비교 기준으로 유지 |
| `challenger_v060/` | 중간 실험 | 허리둘레 결측 추정 적용 |
| `challenger_v061/` | Challenger | 허리 파생변수까지 추가, Test Recall 개선 |

이 실험은 현재 횡단면 위험 신호를 선별한다. KLoSA의 약 2년 후 신규 발병 모델과 데이터·라벨·점수
의미가 다르므로 두 점수를 평균하거나 변화율로 비교하지 않는다. 모델 바이너리와 원자료는 Git에
커밋하지 않는다.
