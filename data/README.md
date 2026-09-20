# 데이터 디렉터리

- `raw/`: 공식 원자료를 로컬에만 보관합니다. Git에 커밋하지 않습니다.
- `raw/*/codebooks/`: 원자료와 동일 공개 버전의 코드북·매핑표·이용지침서를 로컬에 둡니다.
- `interim/`: 조사별 중간 산출물입니다. 재생성 가능해야 합니다.
- `processed/`: split과 코호트가 부여된 최종 모델링 자료입니다.
- `metadata/`: 변수 레지스트리, 병합 검토표, 품질규칙 등 비식별 메타데이터입니다.

원자료를 덮어쓰지 않으며, 공식 파이프라인은 `metadata/official_selected_variable_registry.csv`에 기록된 변수만 사용합니다. 재현 명령은 `python -m src.ml.preprocessing.run_official`입니다.
