# 오늘이·내일이 로컬 모델 연결

모델 바이너리는 Git에 올리지 않는다. 전달받은 `model.joblib`을 저장소 밖에 보관한 뒤 저장소 루트에서 다음 명령으로 배치한다.

```bash
uv run python scripts/provision-models.py \
  --today "/받은/오늘이/model.joblib" \
  --tomorrow "/받은/내일이/model.joblib"
```

Windows PowerShell에서도 같은 명령을 사용할 수 있다. 스크립트는 Manifest의 SHA-256을 확인한 뒤 다음 Git 제외 경로로 복사한다.

- 오늘이: `models/artifacts/candidates/diabetes_current_screening/v050/model.joblib`
- 내일이: `models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib`

그다음 `.env.example`을 `.env`로 복사하고 로컬 비밀값과 DB 값을 입력한 뒤 실행한다.

macOS 최초 설정은 Homebrew가 설치된 상태에서 다음 명령으로 실행한다. 스크립트가 `libomp`를 확인하고 없으면 설치한 뒤 LightGBM·XGBoost import까지 검증한다.

```bash
./scripts/setup-macos.sh
```

```bash
./scripts/start-local.sh
```

현재 두 모델은 후보 모델이므로 실제 추론 성공 여부는 확인할 수 있지만, 운영 승인 전에는 확률과 개인 위험 범주를 사용자 화면에 표시하지 않는다.
