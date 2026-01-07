# Bright Data API Test Script for PowerShell
# This script tests the Bright Data API connection

# Set your API token
$apiToken = "eb2ca709644144656034d231530b20b5a27eff44306808843c78a12019fee95b"

# Set headers
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $apiToken"
}

# Set request body
$body = @{
    zone = "webscrape_amzn"
    url = "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api"
    format = "raw"
} | ConvertTo-Json

# Make the API request
try {
    Write-Host "Testing Bright Data API connection..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "https://api.brightdata.com/request" -Method Post -Headers $headers -Body $body
    
    Write-Host "`nSuccess! Response:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "`nError occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}

