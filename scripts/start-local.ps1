$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCommand) {
    $docker = $dockerCommand.Source
} else {
    $docker = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
}

if (-not (Test-Path -LiteralPath $docker)) {
    throw "Docker CLI를 찾을 수 없습니다. Docker Desktop을 실행한 뒤 다시 시도하세요."
}

# Windows 비ASCII 프로젝트 경로에서 동시 Bake 빌드가 실패하는 문제를 피한다.
$env:COMPOSE_BAKE = "false"

& $docker compose build fastapi
if ($LASTEXITCODE -ne 0) { throw "FastAPI 이미지 빌드에 실패했습니다." }

& $docker compose build ai-worker
if ($LASTEXITCODE -ne 0) { throw "AI Worker 이미지 빌드에 실패했습니다." }

& $docker compose up -d --no-build --remove-orphans
if ($LASTEXITCODE -ne 0) { throw "Docker 서비스 기동에 실패했습니다." }

# 동일 태그를 다시 빌드해도 앱 컨테이너가 이전 이미지로 남지 않도록 교체한다.
& $docker compose up -d --no-build --force-recreate --no-deps fastapi ai-worker nginx
if ($LASTEXITCODE -ne 0) { throw "애플리케이션 컨테이너 교체에 실패했습니다." }

& $docker compose ps
Write-Host "Swagger: http://localhost/api/docs"
Write-Host "Smoke test: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-ai-pipeline.ps1"
