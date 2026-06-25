Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    docker compose -f docker-compose.local.yml ps
    Write-Host ''
    try {
        $Health = Invoke-RestMethod -Uri 'http://localhost:8000/health' -Method Get -TimeoutSec 10
        $Health | ConvertTo-Json -Depth 4
    }
    catch {
        Write-Host 'The orchestrator health endpoint is not reachable.' -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
}
finally {
    Pop-Location
}
