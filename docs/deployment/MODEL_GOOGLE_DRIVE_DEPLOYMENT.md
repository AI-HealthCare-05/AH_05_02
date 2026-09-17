# 오늘이·내일이 Google Drive 모델 배포

## 배포 대상

| 모델 | 버전 | Drive 파일명 | SHA-256 |
|---|---|---|---|
| 오늘이 | `knhanes-today14-sk180-service-v3` | `today-knhanes-today14-sk180-service-v3.joblib` | `2189257587690adfcdf74702f69b516c0a8559cef6059ebd90d003e008c079b1` |
| 내일이 | `rf25-tuned-education4-v2` | `tomorrow-rf25-tuned-education4-v2.joblib` | `45f7de434a887b82aaff86a3b6afd8e99f75ebdc8bb3c0cd320484db9b71ad8e` |

두 모델은 2026-09-17 위험 선별·건강교육 용도로 운영 공개 승인되었다. 진단·처방,
약물 변경 또는 내일이 내부 점수를 개인 발병확률로 표시하는 용도로 사용할 수 없다.

모델과 Manifest는 Google Drive의 `당뇨 모델` 폴더에 보관한다. 원본 의료 데이터와 사용자 입력은 업로드하지 않는다.

## 로컬 또는 EC2 설치

저장소 루트에서 실행한다.

```bash
python3 scripts/provision-models-google-drive.py
```

한 모델만 설치하려면 다음과 같이 실행한다.

```bash
python3 scripts/provision-models-google-drive.py --model today
python3 scripts/provision-models-google-drive.py --model tomorrow
```

다운로드한 바이너리, Drive Manifest, 저장소 Registry의 SHA-256이 모두 같을 때만 `models/artifacts/`에 원자적으로 설치한다. 불일치하면 기존 파일을 교체하지 않는다.

## 배포 순서

1. 배포 브랜치에 Registry, Drive 설정, 프로비저닝 스크립트와 Docker volume 변경을 반영한다.
2. `envs/.prod.env`에 실제 비밀정보와 모델 URI를 설정한다.
   `MODEL_SOURCE_DIR`를 생략하면 EC2의 `~/project/models`를 사용한다.
3. `scripts/deployment.sh`를 실행한다.
4. 스크립트가 EC2에서 모델을 내려받고 SHA-256을 검증한다.
5. 검증 성공 후 AI Worker 이미지를 재기동한다.
6. Worker 로그에서 두 모델의 preload 성공과 버전을 확인한다.
7. 고정 입력 추론 결과와 API의 `model_version`, `threshold_version`, `risk_category`를 확인한다.

## 실패 시 롤백

- SHA-256 불일치 시 배포를 중단하고 Drive 파일 ID와 Registry 해시를 확인한다.
- 한 모델 로딩 실패 시 실패 모델 결과를 생성하지 않으며, 다른 모델 결과는 유지한다.
- 이전 Artifact를 별도 Drive 파일로 보존하고 이전 설정 파일로 되돌린 뒤 Worker만 재기동한다.
- 모델 결과는 진단·처방이 아닌 위험 선별과 건강교육 정보로만 제공한다.
