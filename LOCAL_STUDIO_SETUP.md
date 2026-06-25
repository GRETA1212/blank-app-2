# Local AI Studio — Phase 1

This branch starts a self-hosted content-studio stack designed to avoid mandatory monthly AI and automation subscriptions.

## Included

- **Ollama** for local language models
- **PostgreSQL** for project and pipeline data
- **n8n Community Edition** for local automation
- **FastAPI Studio Orchestrator** for one stable API between the dashboard, Ollama, and future MiroFish integration
- A manual MiroFish seed endpoint; automatic MiroFish submission is intentionally not claimed yet

## Requirements

- Docker Desktop
- Git
- At least 16 GB RAM recommended for `qwen3:8b`; use a smaller model if needed

## Start

```powershell
copy .env.local.example .env

docker compose -f docker-compose.local.yml up -d --build

docker exec -it studio-ollama ollama pull qwen3:8b
```

Open:

- Orchestrator API docs: http://localhost:8000/docs
- n8n: http://localhost:5678
- Ollama: http://localhost:11434
- PostgreSQL host port: 5433

Check services:

```powershell
curl http://localhost:8000/health
```

## Current API

### `POST /ai/generate`

Calls the configured Ollama model locally.

```json
{
  "system": "You are a careful research assistant.",
  "prompt": "Create three original video angles about AI in surveying.",
  "temperature": 0.4
}
```

### `POST /mirofish/seed`

Creates a structured JSON seed for manual upload/testing with MiroFish. It does not pretend that an automatic MiroFish API connection exists.

## MiroFish

Run MiroFish as a separate service from its official repository. During Phase 1:

1. Generate the seed through `/mirofish/seed`.
2. Save the JSON.
3. Upload/use it manually in MiroFish.
4. Bring the report back to the control center for structured analysis.

Automatic connectivity comes only after the real MiroFish backend routes are inspected and tested.

## Cost boundary

The software in this stack is self-hosted. It avoids mandatory per-request AI charges when using Ollama, but it still consumes local electricity, CPU/GPU, memory, and storage. Optional cloud APIs can be connected later without changing the core architecture.

## Next development steps

1. Add database migrations for workspaces, ideas, projects, simulations, and performance entries.
2. Add authentication before exposing the service outside localhost.
3. Add strict JSON schemas for research, scripts, scenes, and quality review.
4. Connect the React Studio Control Center frontend.
5. Inspect and implement a tested MiroFish provider.
6. Add n8n workflows for approved-project rendering only.
