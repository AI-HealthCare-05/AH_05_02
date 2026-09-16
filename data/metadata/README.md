# 통합 메타데이터

| 파일 | 용도 |
| --- | --- |
| `unified_variable_registry.csv` | KLoSA·KNHANES 공통 개념과 원변수, 역할, 단위, 결측코드, 승인 상태 |
| `merge_review_queue.csv` | 자동 병합된 의미 변수의 수동 검토 대기표 |
| `source_inventory.csv` | 입력 파일 위치·크기·SHA-256·확보 상태 |
| `cohort_definitions.csv` | 19+·40+·65+ 누적 코호트 정의 |
| `quality_rules.csv` | 전처리 품질문과 차단 조건 |
| `quality_summary.json` | 현재 실행 가능 여부 요약 |

`review_status`가 `approved` 또는 `approved_with_note`가 아닌 변수는 실제 전처리에 사용되지 않습니다. `missing_codes`, `unit`, `valid_min`, `valid_max`, `codebook_page_or_table`은 공식 코드북을 확인한 뒤 입력합니다.
