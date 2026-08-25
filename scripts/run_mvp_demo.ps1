$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $workspaceRoot

$storagePath = Join-Path $workspaceRoot "storage"
New-Item -ItemType Directory -Path $storagePath -Force | Out-Null

$env:DEMO_MODE = "true"
$env:DB_GENERATE_SCHEMAS = "true"
$env:DATABASE_URL = "sqlite://storage/gandang_mvp.sqlite3"
$env:SECRET_KEY = "local-demo-only-change-before-deployment"

& ".venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000
