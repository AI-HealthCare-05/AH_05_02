param(
    [switch]$SkipInstall,
    [switch]$SkipTests
)

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$taskUvCache = Join-Path $projectRoot "tmp\uv-cache"
$taskVenv = Join-Path $projectRoot ".venv"
$taskEnvExample = Join-Path $projectRoot ".env.example"
$taskEnvLocal = Join-Path $projectRoot ".env"

Set-Location -LiteralPath $projectRoot

Write-Host "[1/6] 필수 명령 확인"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git이 설치되어 있지 않습니다. Git for Windows를 먼저 설치하세요."
}

Write-Host "[2/6] uv 확인"
$taskUvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $taskUvCommand) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python과 uv가 모두 없습니다. https://docs.astral.sh/uv/getting-started/installation/ 에서 uv를 설치한 뒤 다시 실행하세요."
    }
    python -m pip install --user uv
    if ($LASTEXITCODE -ne 0) {
        throw "uv 설치에 실패했습니다."
    }
    $taskUvExecutable = Get-ChildItem -Path (Join-Path $env:APPDATA 'Python') -Filter 'uv.exe' -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName
    if (-not $taskUvExecutable -or -not (Test-Path -LiteralPath $taskUvExecutable)) {
        throw "uv.exe를 찾지 못했습니다. 새 PowerShell을 열고 다시 실행하세요."
    }
} else {
    $taskUvExecutable = $taskUvCommand.Source
}

$env:UV_CACHE_DIR = $taskUvCache

if (-not $SkipInstall) {
    Write-Host "[3/6] Python 3.13 및 가상환경 구성"
    & $taskUvExecutable python install 3.13
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.13 설치에 실패했습니다."
    }
    & $taskUvExecutable venv $taskVenv --python 3.13
    if ($LASTEXITCODE -ne 0) {
        throw "가상환경 생성에 실패했습니다."
    }

    Write-Host "[4/6] 프로젝트 의존성 설치"
    & $taskUvExecutable sync --all-groups --frozen --python 3.13
    if ($LASTEXITCODE -ne 0) {
        throw "의존성 설치에 실패했습니다."
    }
} else {
    Write-Host "[3/6] Python·가상환경 설치 생략"
    Write-Host "[4/6] 의존성 설치 생략"
}

Write-Host "[5/6] 로컬 환경변수 파일 확인"
if (-not (Test-Path -LiteralPath $taskEnvLocal)) {
    Copy-Item -LiteralPath $taskEnvExample -Destination $taskEnvLocal
    Write-Host ".env를 .env.example에서 생성했습니다. 비밀값은 직접 입력하세요."
} else {
    Write-Host "기존 .env를 보존했습니다."
}

if (-not $SkipTests) {
    Write-Host "[6/6] 테스트 실행"
    # 새 PC의 .env는 Docker용 MySQL 주소를 사용한다. 초기 설치 검사는 외부 DB나
    # 모델 바이너리에 의존하지 않는 SQLite/development 모드로 분리한다.
    $previousDemoMode = $env:DEMO_MODE
    $previousDatabaseUrl = $env:DATABASE_URL
    $previousSecretKey = $env:SECRET_KEY
    $previousPredictionProvider = $env:PREDICTION_PROVIDER
    $previousS2Runtime = $env:S2_MODEL_RUNTIME_ENABLED
    try {
        $env:PYTHONUTF8 = "1"
        $env:DEMO_MODE = "true"
        $env:DATABASE_URL = "sqlite://:memory:"
        $env:SECRET_KEY = "setup-test-only-not-for-deployment"
        $env:PREDICTION_PROVIDER = "development"
        $env:S2_MODEL_RUNTIME_ENABLED = "false"
        & "$taskVenv\Scripts\python.exe" -m pytest --ignore=tests/backend/api --basetemp=tmp/setup-pytest -p no:cacheprovider
    }
    finally {
        $env:DEMO_MODE = $previousDemoMode
        $env:DATABASE_URL = $previousDatabaseUrl
        $env:SECRET_KEY = $previousSecretKey
        $env:PREDICTION_PROVIDER = $previousPredictionProvider
        $env:S2_MODEL_RUNTIME_ENABLED = $previousS2Runtime
    }
    if ($LASTEXITCODE -ne 0) {
        throw "테스트가 실패했습니다. 위 오류를 확인하세요."
    }
} else {
    Write-Host "[6/6] 테스트 생략"
}

Write-Host ""
Write-Host "Windows 로컬 초기 설정이 완료되었습니다."
Write-Host "가상환경 활성화: .\.venv\Scripts\Activate.ps1"
Write-Host "서버 실행: python -m uvicorn app.main:app --reload"
Write-Host "Swagger: http://localhost:8000/api/docs"
