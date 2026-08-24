param([string]$BaseUrl = "http://localhost")

$ErrorActionPreference = "Stop"
$stamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$suffix = ($stamp % 100000000).ToString("00000000")
$email = "sprint2-$stamp@example.com"
$phone = "010$suffix"
$password = "Sprint2Test!9"

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [string]$Token = ""
    )
    $headers = @{}
    if ($Token) { $headers.Authorization = "Bearer $Token" }
    $parameters = @{
        Method = $Method
        Uri = "$BaseUrl/api/v1$Path"
        Headers = $headers
        ContentType = "application/json"
    }
    if ($null -ne $Body) { $parameters.Body = ($Body | ConvertTo-Json -Depth 10) }
    return Invoke-RestMethod @parameters
}

Invoke-Api POST "/auth/signup" @{
    email = $email
    password = $password
    name = "스모크테스트"
    gender = "FEMALE"
    birth_date = "1965-04-12"
    phone_number = $phone
} | Out-Null
$login = Invoke-Api POST "/auth/login" @{ email = $email; password = $password }
$token = $login.access_token

$consent = Invoke-Api POST "/consents" @{ consent_item = "health_data"; version = "1.0"; is_agreed = $true } $token
$eligibility = Invoke-Api POST "/eligibility-checks" @{
    birth_date = "1965-04-12"
    has_diabetes_diagnosis = $false
    has_urgent_warning_sign = $false
    population_in_scope = $true
} $token
if (-not $eligibility.data.model_eligible) { throw "Expected model_eligible=true" }

$checkup = Invoke-Api POST "/health-checkups" @{
    checkup_type = "initial"
    checkup_date = (Get-Date).ToString("yyyy-MM-dd")
    height_cm = 160
    weight_kg = 67.5
    waist_cm = 91
    systolic_bp = 130
    diastolic_bp = 80
    self_rated_health = "fair"
    meal_count_yesterday = 3
    regular_exercise = $true
    current_smoker = $false
    current_drinker = $false
    feature_schema_version = "klosa-diabetes-incident-v1"
} $token

$job = Invoke-Api POST "/prediction-jobs" @{
    checkup_id = $checkup.data.checkup_id
    model_key = "diabetes_incidence"
} $token
for ($attempt = 1; $attempt -le 30; $attempt++) {
    $current = Invoke-Api GET "/prediction-jobs/$($job.data.job_id)" $null $token
    if ($current.data.status -eq "succeeded") { break }
    if ($current.data.status -eq "failed") { throw "Prediction failed: $($current.data.error_code)" }
    Start-Sleep -Milliseconds 500
}
if ($current.data.status -ne "succeeded") { throw "Prediction polling timed out" }

$prediction = Invoke-Api GET "/predictions/$($current.data.prediction_id)" $null $token
if ($prediction.data.result_status -ne "development_only") { throw "Expected development_only result" }
if ($null -ne $prediction.data.risk_category) { throw "Unapproved risk category must not be public" }

$recommendations = Invoke-Api GET "/challenge-recommendations?prediction_id=$($prediction.data.prediction_id)" $null $token
$challengeId = $recommendations.data.items[0].challenge_id
$cycle = Invoke-Api POST "/challenge-cycles" @{
    start_date = (Get-Date).ToString("yyyy-MM-dd")
    challenge_ids = @($challengeId)
    prediction_id = $prediction.data.prediction_id
} $token
$userChallengeId = $cycle.data.user_challenges[0].user_challenge_id
Invoke-Api PUT "/user-challenges/$userChallengeId/logs/$((Get-Date).ToString('yyyy-MM-dd'))" @{
    is_completed = $true
    source = "self_report"
} $token | Out-Null
$dashboard = Invoke-Api GET "/dashboard/summary" $null $token
if ($dashboard.data.current_cycle.cycle_id -ne $cycle.data.cycle_id) { throw "Dashboard cycle mismatch" }

$diagnosed = Invoke-Api POST "/eligibility-checks" @{
    birth_date = "1965-04-12"
    has_diabetes_diagnosis = $true
    has_urgent_warning_sign = $false
    population_in_scope = $true
} $token
if ($diagnosed.data.model_eligible) { throw "Diagnosed user must be blocked" }
$followUps = Invoke-Api GET "/follow-up-actions" $null $token
if ($followUps.data.items.Count -lt 1) { throw "Expected medical follow-up action" }

$urgent = Invoke-Api POST "/eligibility-checks" @{
    birth_date = "1965-04-12"
    has_diabetes_diagnosis = $false
    has_urgent_warning_sign = $true
    population_in_scope = $true
} $token
if ($urgent.data.next_action -ne "urgent_medical_guidance") { throw "Urgent warning must precede challenges" }

$secondEmail = "no-consent-$stamp@example.com"
$secondSuffix = (($stamp + 1) % 100000000).ToString("00000000")
$secondPhone = "010$secondSuffix"
Invoke-Api POST "/auth/signup" @{
    email = $secondEmail
    password = $password
    name = "미동의테스트"
    gender = "MALE"
    birth_date = "1960-01-01"
    phone_number = $secondPhone
} | Out-Null
$secondLogin = Invoke-Api POST "/auth/login" @{ email = $secondEmail; password = $password }
$secondToken = $secondLogin.access_token
$noConsent = Invoke-Api POST "/eligibility-checks" @{
    birth_date = "1960-01-01"
    has_diabetes_diagnosis = $false
    has_urgent_warning_sign = $false
    population_in_scope = $true
} $secondToken
if ($noConsent.data.reason_codes -notcontains "CONSENT_REQUIRED") { throw "Missing consent must be explicit" }
try {
    Invoke-Api GET "/predictions/$($prediction.data.prediction_id)" $null $secondToken | Out-Null
    throw "Cross-user prediction access must fail"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 404) { throw }
}

Write-Output ([ordered]@{
    status = "ok"
    consent_id = $consent.data.consent_id
    checkup_id = $checkup.data.checkup_id
    job_status = $current.data.status
    prediction_result_status = $prediction.data.result_status
    risk_category_exposed = ($null -ne $prediction.data.risk_category)
    cycle_id = $cycle.data.cycle_id
    diagnosed_prediction_blocked = (-not $diagnosed.data.model_eligible)
    consent_missing_blocked = ($noConsent.data.reason_codes -contains "CONSENT_REQUIRED")
    urgent_guidance_first = ($urgent.data.next_action -eq "urgent_medical_guidance")
    cross_user_access_blocked = $true
} | ConvertTo-Json)
