# Usage: .\run_predict_timed.ps1 [base_url]
# Example: .\run_predict_timed.ps1                    # local: http://127.0.0.1:8000
# Example: .\run_predict_timed.ps1 https://trade-bot-api.onrender.com
param([string]$BaseUrl = "http://127.0.0.1:8000")
$body = '{"symbols": ["TATASTEEL.NS"], "horizon": "intraday"}'
$start = Get-Date
Write-Host "Base URL: $BaseUrl"
Write-Host "Starting async predict..."
try {
  $r = Invoke-RestMethod -Uri "$BaseUrl/tools/predict/async" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 60
} catch {
  Write-Host "ERROR: Could not reach backend. Is it running? $($_.Exception.Message)"
  exit 1
}
$jobId = $r.job_id
if (-not $jobId) { Write-Host "ERROR: No job_id in response"; exit 1 }
Write-Host "Job ID: $jobId (polling every 5s)..."
$url = "$BaseUrl/tools/predict/result/$jobId"
$pollCount = 0
while ($true) {
  $pollCount++
  try {
    $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 90
  } catch {
    Write-Host "Poll $pollCount error: $($_.Exception.Message)"
    Start-Sleep -Seconds 5
    continue
  }
  if ($resp.StatusCode -eq 200) {
    $elapsed = ((Get-Date) - $start).TotalSeconds
    Write-Host ""
    Write-Host "RESULT in $([math]::Round($elapsed, 1))s" -ForegroundColor Green
    Write-Host ($resp.Content.Substring(0, [Math]::Min(800, $resp.Content.Length)))
    exit 0
  }
  if ($resp.StatusCode -eq 404) { Write-Host "ERROR: Job not found or expired"; exit 1 }
  Write-Host "Poll $pollCount - status $($resp.StatusCode) - waiting 5s"
  Start-Sleep -Seconds 5
}
