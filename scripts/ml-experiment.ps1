param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("validate", "list", "new", "run", "leaderboard", "register-candidate")]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Value,

    [ValidateSet("baseline", "candidate", "ensemble")]
    [string]$Kind,

    [string]$Owner
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$Arguments = @("--cache-dir", ".uv-cache", "run", "python", "-m", "src.ml.experiments.runner", $Command)
if ($Value) {
    $Arguments += $Value
}
if ($Kind) {
    $Arguments += @("--kind", $Kind)
}
if ($Owner) {
    $Arguments += @("--owner", $Owner)
}

& uv @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "ML experiment command failed with exit code $LASTEXITCODE"
}
