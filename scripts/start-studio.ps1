Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker Desktop is required. Install and start Docker Desktop first.'
    }

    docker info | Out-Null

    if (-not (Test-Path '.env')) {
        Copy-Item '.env.local.example' '.env'
        Write-Host 'Created .env from .env.local.example. Review the password before exposing anything outside this PC.' -ForegroundColor Yellow
    }

    Write-Host 'Building and starting Studio Control Center...' -ForegroundColor Cyan
    docker compose -f docker-compose.local.yml up -d --build

    $ModelLine = Get-Content '.env' | Where-Object { $_ -match '^OLLAMA_MODEL=' } | Select-Object -First 1
    $Model = if ($ModelLine) { ($ModelLine -split '=', 2)[1].Trim() } else { 'qwen3:8b' }

    Write-Host "Ensuring Ollama model $Model is installed..." -ForegroundColor Cyan
    docker exec studio-ollama ollama pull $Model

    Write-Host ''
    Write-Host 'Studio Control Center: http://localhost:3000' -ForegroundColor Green
    Write-Host 'Node-RED:             http://localhost:1880' -ForegroundColor Green
    Write-Host 'API documentation:    http://localhost:8000/docs' -ForegroundColor Green
    Write-Host 'SearXNG:               http://localhost:8080' -ForegroundColor Green
    Write-Host ''
    Write-Host 'MiroFish remains a separate optional service. Manual seed/report mode works without it.' -ForegroundColor Yellow

    Start-Process 'http://localhost:3000'
}
finally {
    Pop-Location
}
