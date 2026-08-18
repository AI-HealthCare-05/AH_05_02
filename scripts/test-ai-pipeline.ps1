param(
    [string]$BaseUrl = "http://localhost"
)

$ErrorActionPreference = "Stop"
$body = @{
    task_type = "demo_inference"
    payload = @{
        source = "windows-smoke-test"
        message = "pipeline-ready"
    }
} | ConvertTo-Json -Depth 5

$job = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/ai-jobs" -ContentType "application/json" -Body $body
Write-Host "Queued job: $($job.job_id)"

for ($attempt = 1; $attempt -le 30; $attempt++) {
    $current = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/v1/ai-jobs/$($job.job_id)"
    Write-Host "[$attempt/30] status=$($current.status) worker=$($current.worker_name)"
    if ($current.status -eq "completed") {
        $current | ConvertTo-Json -Depth 10
        exit 0
    }
    if ($current.status -eq "failed") {
        $current | ConvertTo-Json -Depth 10
        exit 1
    }
    Start-Sleep -Seconds 1
}

throw "AI job did not complete within 30 seconds."
