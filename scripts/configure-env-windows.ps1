Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envDirectory = Join-Path $projectRoot "envs"
$rootEnv = Join-Path $projectRoot ".env"
$localEnv = Join-Path $envDirectory ".local.env"
$prodEnv = Join-Path $envDirectory ".prod.env"
$legacyEnv = Join-Path $envDirectory ".legacy.env"

if (-not $envDirectory.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "ENV directory resolved outside the project root."
}

New-Item -ItemType Directory -Path $envDirectory -Force | Out-Null

function New-ProjectSecret {
    param([int]$ByteCount = 36)

    $bytes = [byte[]]::new($ByteCount)
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Read-EnvValues {
    param([string]$Path)

    $values = [ordered]@{}
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

function Write-EnvValues {
    param(
        [string]$Path,
        [System.Collections.IDictionary]$Values
    )

    $lines = foreach ($entry in $Values.GetEnumerator()) {
        "{0}={1}" -f $entry.Key, $entry.Value
    }
    [System.IO.File]::WriteAllLines($Path, $lines, [System.Text.UTF8Encoding]::new($false))
}

$existingSource = if (Test-Path -LiteralPath $rootEnv) {
    $rootEnv
}
elseif (Test-Path -LiteralPath $legacyEnv) {
    $legacyEnv
}
else {
    $localEnv
}
$existingValues = Read-EnvValues -Path $existingSource

$localValues = [ordered]@{
    ENV = "local"
    DOCKER_USER = "local"
    DOCKER_REPOSITORY = "ah-05-02"
    APP_VERSION = "v0.1.0"
    SECRET_KEY = New-ProjectSecret
    COOKIE_DOMAIN = "localhost"
    AI_WORKER_VERSION = "v0.1.0"
    DB_HOST = "mysql"
    DB_PORT = "3306"
    DB_EXPOSE_PORT = "3306"
    DB_USER = "ah05_app"
    DB_PASSWORD = New-ProjectSecret -ByteCount 24
    DB_ROOT_PASSWORD = New-ProjectSecret -ByteCount 30
    DB_NAME = "ah05_healthcare"
    REDIS_PORT = "6379"
}

foreach ($entry in $existingValues.GetEnumerator()) {
    if (-not $localValues.Contains($entry.Key)) {
        $localValues[$entry.Key] = $entry.Value
    }
}

$prodValues = [ordered]@{
    ENV = "prod"
    DOCKER_USER = "CHANGE_ME"
    DOCKER_REPOSITORY = "ah-05-02"
    APP_VERSION = "v0.1.0"
    SECRET_KEY = New-ProjectSecret
    COOKIE_DOMAIN = "CHANGE_ME"
    AI_WORKER_VERSION = "v0.1.0"
    DB_HOST = "mysql"
    DB_PORT = "3306"
    DB_EXPOSE_PORT = "3306"
    DB_USER = "ah05_app"
    DB_PASSWORD = New-ProjectSecret -ByteCount 24
    DB_ROOT_PASSWORD = New-ProjectSecret -ByteCount 30
    DB_NAME = "ah05_healthcare"
    REDIS_PORT = "6379"
}

Write-EnvValues -Path $localEnv -Values $localValues
Write-EnvValues -Path $prodEnv -Values $prodValues

if (Test-Path -LiteralPath $rootEnv) {
    $rootEnvItem = Get-Item -LiteralPath $rootEnv -Force
    if ($rootEnvItem.LinkType -ne "SymbolicLink") {
        if (-not (Test-Path -LiteralPath $legacyEnv)) {
            Move-Item -LiteralPath $rootEnv -Destination $legacyEnv
        }
        else {
            Remove-Item -LiteralPath $rootEnv -Force
        }
    }
    else {
        Remove-Item -LiteralPath $rootEnv -Force
    }
}

$linkType = "SymbolicLink"
try {
    New-Item -ItemType SymbolicLink -Path $rootEnv -Target $localEnv -ErrorAction Stop | Out-Null
}
catch [System.UnauthorizedAccessException] {
    New-Item -ItemType HardLink -Path $rootEnv -Target $localEnv | Out-Null
    $linkType = "HardLink"
}

Write-Output "Local and production ENV files created."
Write-Output "Existing ENV keys preserved: $($existingValues.Count)"
Write-Output "Root .env now links to envs/.local.env using $linkType."
