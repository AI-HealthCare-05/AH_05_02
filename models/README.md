# 모델 관리

대용량 모델 파일은 Git에 커밋하지 않습니다. 모델 버전, 학습 설정, 성능, 체크섬과 외부 저장 위치를 기록합니다.

- 실제 바이너리: `models/artifacts/` 또는 외부 S3, Git 제외
- 후보·운영 manifest: `models/registry/<model_key>/`, Git 공유
- 후보 등록과 운영 활성화를 분리하며 승인 전 개인 위험확률을 서비스하지 않습니다.
