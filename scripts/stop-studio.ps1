Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    docker compose -f docker-compose.local.yml down
    Write-Host 'Studio services stopped. Database, models, jobs, and media remain in Docker volumes.' -ForegroundColor Green
}
finally {
    Pop-Location
}
