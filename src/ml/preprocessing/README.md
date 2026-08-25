# 전처리 코드

KLoSA·KNHANES 원본을 읽어 `data/interim/`과 `data/processed/official_v1/`을 생성하는 코드만 둡니다.

- 원본 파일과 생성 CSV는 Git에 올리지 않습니다.
- 결측·라벨·코호트 기준 변경 시 `data/metadata/`와 테스트를 함께 수정합니다.
- 전체 데이터로 전처리 통계를 학습한 뒤 분리하지 않습니다. 학습용 통계는 Train에서만 적합합니다.
