# 1) Start async prediction (no long wait)
$body = '{"symbols": ["TATASTEEL.NS"], "horizon": "intraday"}'
$r = Invoke-RestMethod -Uri "https://trade-bot-api.onrender.com/tools/predict/async" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 120
$jobId = $r.job_id
Write-Host "Job: $jobId -- polling until 200 (no timeout)..."
$url = "https://trade-bot-api.onrender.com/tools/predict/result/$jobId"

# 2) Poll until 200
while ($true) {
  try {
    $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 90
    if ($resp.StatusCode -eq 200) {
      Write-Host "`n--- RESULT ---"
      $resp.Content
      break
    }
    Write-Host "202 - running... next in 30s"
  } catch {
    Write-Host "Poll error/timeout, retry in 30s"
  }
  Start-Sleep -Seconds 30
}
