param([string]$BaseUrl = "http://localhost")

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $scriptRoot "test-sprint2-flow.ps1") -BaseUrl $BaseUrl
