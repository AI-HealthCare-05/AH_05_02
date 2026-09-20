# Windows 개발환경 초기 설정 가이드

이 문서는 Windows 11, PowerShell, PyCharm을 기준으로 한다. 현재 팀 저장소는 이미 생성되어 있으므로 팀장과 팀원의 시작 방법이 다르다.

## 1. 저장소 준비

### 팀장: 기존 저장소 사용

팀장은 이미 다음 저장소를 사용하고 있으므로 템플릿을 다시 복제하거나 `origin`을 삭제하지 않는다.

```powershell
$projectRoot = Join-Path $env:USERPROFILE 'PycharmProjects\AH_05_02'
Set-Location -LiteralPath $projectRoot
git remote -v
git status --short --branch
```

원격 저장소:

```text
https://github.com/AI-HealthCare-05/AH_05_02.git
```

### 팀원: 저장소 최초 복제

```powershell
$projectParent = Join-Path $env:USERPROFILE 'PycharmProjects'
New-Item -ItemType Directory -Path $projectParent -Force
Set-Location -LiteralPath $projectParent
git clone https://github.com/AI-HealthCare-05/AH_05_02.git
Set-Location -LiteralPath (Join-Path $projectParent 'AH_05_02')
```

> `git clone` 대상 폴더가 이미 존재하면 다시 복제하지 말고 기존 폴더에서 `git status`와 `git remote -v`를 확인한다.

## 2. Git 개인 설정

각 팀원은 자신의 이름과 GitHub 이메일을 입력한다.

```powershell
git config --global user.name '본인 이름'
git config --global user.email '본인 GitHub 이메일'
git config --global core.autocrlf true

git config --get user.name
git config --get user.email
```

팀장 PC의 현재 설정:

```text
user.name  = 본인 이름
user.email = 본인 GitHub 이메일
```

저장소 규칙에 따라 `main`과 `develop`에 직접 Push하지 않고 Issue와 feature 브랜치, Pull Request를 사용한다.

```powershell
git switch -c feature/이슈번호-작업명
```

## 3. PyCharm에서 열기

PyCharm에서 `File > Open`을 선택하고 저장소 루트를 연다.

명령줄 실행기가 등록되어 있다면 다음과 같이 열 수 있다.

```powershell
pycharm $projectRoot
```

팀장 PC에서는 다음 실행 파일이 확인되었다.

```powershell
& '<PyCharm 설치 경로>\bin\pycharm64.exe' $projectRoot
```

## 4. 자동 초기 설정

PowerShell 실행 정책 때문에 스크립트가 차단될 수 있으므로 현재 프로세스에서만 허용한 뒤 실행한다.

```powershell
Set-Location -LiteralPath '프로젝트 루트 경로'
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-windows.ps1
```

스크립트가 수행하는 작업:

1. Git과 Python 확인
2. `uv` 설치 또는 확인
3. Python 3.13 설치
4. `.venv` 가상환경 생성
5. `pyproject.toml`·`uv.lock` 의존성 설치
6. `.env` 생성 여부 확인
7. 테스트 실행

현재 저장소의 `pyproject.toml`과 `uv.lock`을 기준으로 다음 방식을 사용한다.

```powershell
uv venv .venv --python 3.13
uv sync --all-groups --frozen --python 3.13
```

## 5. 가상환경과 PyCharm 인터프리터

PowerShell에서 활성화:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
```

PyCharm에서는 다음 인터프리터를 선택한다.

```text
프로젝트 루트\.venv\Scripts\python.exe
```

경로: `Settings > Project > Python Interpreter > Add Interpreter > Existing`

## 6. 환경변수

Windows에서는 `cp` 대신 `Copy-Item`을 사용한다.

```powershell
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
```

현재 프로젝트는 `.env`를 저장소 루트에서 직접 사용한다. Windows 심볼릭 링크는 관리자 권한 또는 개발자 모드가 필요하므로 사용하지 않는다.

`.env`에 실제 값을 입력하되 다음 원칙을 지킨다.

- `.env`는 Git에 커밋하지 않는다.
- `.env.example`에는 변수명과 공개 가능한 예시만 기록한다.
- API 키, DB 비밀번호, JWT 비밀키를 메신저나 공개 문서에 올리지 않는다.
- 팀 공통 배포 비밀값은 GitHub Secrets 또는 배포 서버의 환경변수로 관리한다.

현재 변수:

```dotenv
APP_ENV=local
DATABASE_URL=
JWT_SECRET_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=
CLOVA_OCR_URL=
CLOVA_OCR_SECRET=
```

## 7. 로컬 실행 및 테스트

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest
python -m uvicorn app.main:app --reload
```

확인 주소:

- 웹 프로토타입: <http://localhost:8000/>
- Swagger UI: <http://localhost:8000/api/docs>
- 상태 확인: <http://localhost:8000/health>

현재 Compose 설정의 외부 포트도 `8000`이므로 `/api/docs`가 아니라 `/docs`를 사용한다.

## 8. Docker Desktop

Docker가 설치되어 있다면 다음 명령으로 확인한다.

```powershell
docker --version
docker compose version
docker compose config
docker compose up --build -d
docker compose ps
```

중지:

```powershell
docker compose down
```

팀장 PC에서는 현재 `docker` 명령이 확인되지 않았다. Docker Desktop 설치 후 새 PowerShell을 열고 다시 확인해야 한다.

## 9. Windows 포트 충돌 확인

Linux의 `lsof` 대신 `Get-NetTCPConnection`을 사용한다.

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess

Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess

Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess
```

프로세스 확인:

```powershell
Get-Process -Id '위에서 확인한 PID'
```

정말 종료해도 되는 프로세스인지 확인한 뒤에만 실행한다.

```powershell
Stop-Process -Id '확인한 PID'
```

## 10. 팀장 설정 점검표

- [x] 팀 원격 저장소 연결
- [x] Public 저장소 생성
- [x] Git 사용자 이름·이메일 설정
- [x] Python 3.13 프로젝트 가상환경 구성
- [x] 로컬 의존성 설치
- [x] `.env` 골격 생성 및 Git 제외
- [ ] GitHub CLI 재로그인
- [ ] 팀원의 초대 수락 상태 확인
- [ ] 브랜치 보호 또는 Ruleset 설정
- [ ] Docker Desktop 설치
- [ ] 팀 공통 배포 환경변수 합의
- [ ] GitHub Secrets 등록

## 11. 개인 설정 점검표

- [x] PyCharm 설치 확인
- [x] `uv` 설치 (`python -m uv`로 실행 가능)
- [x] Python 3.13 설치
- [x] `.venv` 생성
- [x] 의존성 설치
- [ ] PyCharm 인터프리터를 `.venv\Scripts\python.exe`로 선택
- [ ] `.env`의 개인 로컬 비밀값 입력
- [ ] Docker Desktop 설치 후 Compose 실행 확인
- [ ] GitHub CLI 로그인 확인

## 12. GitHub CLI 재로그인

현재 저장된 GitHub CLI 인증 토큰이 만료되어 있다. 다음 명령을 본인이 실행하고 브라우저 인증을 완료한다.

```powershell
gh auth login -h github.com -p https --web
gh auth status
```
