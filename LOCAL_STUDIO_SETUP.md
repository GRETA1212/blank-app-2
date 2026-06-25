# Local Studio Setup

The repository now contains the full local MVP. The main guide is in `README.md`; this file is the condensed startup checklist.

## Included services

- React Studio Control Center — port 3000
- FastAPI Studio Orchestrator — port 8000
- PostgreSQL — host port 5433
- Ollama — port 11434
- SearXNG — port 8080
- Local FFmpeg/eSpeak media worker — port 9000
- Node-RED — port 1880
- Optional separate MiroFish installation — normally port 5001

## Windows startup

```powershell
git switch feature/local-ai-studio
powershell -ExecutionPolicy Bypass -File .\scripts\start-studio.ps1
```

The script creates `.env`, builds the containers, starts the services, downloads the configured Ollama model, and opens the dashboard.

## Manual startup

```powershell
copy .env.local.example .env
docker compose -f docker-compose.local.yml up -d --build
docker exec studio-ollama ollama pull qwen3:8b
```

## Health check

```powershell
.\scripts\status-studio.ps1
```

Or open:

```text
http://localhost:8000/health
```

## Stop

```powershell
.\scripts\stop-studio.ps1
```

## MiroFish boundary

The dashboard generates seed JSON and imports completed reports. Automatic submission is intentionally not claimed until the installed MiroFish backend routes are inspected and tested.

## Security boundary

This release is local single-user software. Do not forward or publicly expose the database, Ollama, SearXNG, orchestrator, Node-RED, media-worker, or MiroFish ports.
