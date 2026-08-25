# 당뇨병 미래발병 모델 레지스트리

- `candidates/`: 실험 제약을 통과한 후보 manifest. 자동 등록할 수 있습니다.
- `active.json`: 팀 검토·재현·의료 안전 확인을 마친 운영 모델 하나만 기록합니다.
- 실제 `.joblib`, `.pkl`, `.pt`, `.onnx` 파일은 Git에 올리지 않습니다.

후보 등록은 운영 활성화가 아닙니다. 웹서비스의 `PREDICTION_PROVIDER=artifact` 전환은 모델 버전, 입력 스키마, 임계값 버전과 checksum을 검토한 뒤 별도 PR로 수행합니다.
