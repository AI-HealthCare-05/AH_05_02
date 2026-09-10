[CmdletBinding()]
param(
    [string]$EnvironmentFile = "envs/.prod.env",
    [string]$AwsProfile = "ah05",
    [string]$AwsRegion = "ap-northeast-2",
    [switch]$SkipDocker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$environmentPath = Join-Path $projectRoot $EnvironmentFile
$problems = [System.Collections.Generic.List[string]]::new()

function Test-CommandAvailable {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Read-EnvironmentKeys {
    param([string]$Path)
    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $values[$matches[1]] = $matches[2]
        }
    }
    return $values
}

Write-Output "[1/5] Checking AWS CLI session"
$awsInfo = Get-Command "aws" -ErrorAction SilentlyContinue
$awsCommand = if ($awsInfo) { $awsInfo.Source } else { $null }
if (-not $awsCommand) {
    $standardAwsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
    if (Test-Path -LiteralPath $standardAwsPath) {
        $awsCommand = $standardAwsPath
    }
}
if (-not $awsCommand) {
    $problems.Add("AWS CLI is not installed or is not available on PATH.")
}
else {
    try {
        $identity = & $awsCommand sts get-caller-identity --profile $AwsProfile --region $AwsRegion --output json | ConvertFrom-Json
        Write-Output ("AWS account: {0}, principal: {1}" -f $identity.Account, $identity.Arn)
    }
    catch {
        $problems.Add("AWS CLI credentials are unavailable. Console and CLI sessions are separate.")
    }
}

Write-Output "[2/5] Checking production environment keys"
$values = Read-EnvironmentKeys -Path $environmentPath
$required = @(
    "ENV", "SECRET_KEY", "COOKIE_DOMAIN", "DB_USER", "DB_PASSWORD", "DB_ROOT_PASSWORD", "DB_NAME",
    "PREDICTION_PROVIDER", "MODEL_URI", "MODEL_MANIFEST_URI", "CURRENT_SCREENING_MODEL_URI",
    "CURRENT_SCREENING_MANIFEST_URI", "MODEL_ARTIFACTS_PATH"
)
foreach ($key in $required) {
    if (-not $values.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($values[$key]) -or $values[$key] -eq "CHANGE_ME") {
        $problems.Add("Missing production value: $key")
    }
}
if ($values.ContainsKey("ENV") -and $values["ENV"] -ne "prod") {
    $problems.Add("ENV must be prod.")
}

Write-Output "[3/5] Checking model artifacts and manifests"
$modelPairs = @(
    @("MODEL_URI", "MODEL_MANIFEST_URI"),
    @("CURRENT_SCREENING_MODEL_URI", "CURRENT_SCREENING_MANIFEST_URI")
)
foreach ($pair in $modelPairs) {
    foreach ($key in $pair) {
        if ($values.ContainsKey($key) -and -not $values[$key].StartsWith("s3://")) {
            $relative = $values[$key] -replace '^/app/', ''
            $candidate = Join-Path $projectRoot $relative
            if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
                $problems.Add("Missing file: $key -> $($values[$key])")
            }
        }
    }
}

Write-Output "[4/5] Checking Docker runtime"
if (-not $SkipDocker) {
    if (-not (Test-CommandAvailable "docker")) {
        $problems.Add("Docker is not installed.")
    }
    else {
        try {
            docker info | Out-Null
            docker compose -f (Join-Path $projectRoot "infra/docker/docker-compose.prod.yml") --env-file $environmentPath config --quiet
        }
        catch {
            $problems.Add("Docker engine or production Compose validation failed.")
        }
    }
}

Write-Output "[5/5] Checking Git state"
Push-Location $projectRoot
try {
    $dirty = git status --porcelain
    if ($dirty) {
        $problems.Add("The worktree is dirty. Deploy from a reviewed commit.")
    }
}
finally {
    Pop-Location
}

if ($problems.Count -gt 0) {
    Write-Output ""
    Write-Output "Deployment preflight failed:"
    $problems | ForEach-Object { Write-Output "- $_" }
    exit 1
}

Write-Output ""
Write-Output "Deployment preflight passed."
