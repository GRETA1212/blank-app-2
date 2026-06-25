# Studio Control Center

A local-first control center for researching, creating, reviewing, simulating, rendering, and tracking YouTube/TikTok content.

The project is designed to run on your own computer with open-source or locally hosted components, so there is no mandatory per-request AI subscription.

## What works

- Current public-web research through self-hosted SearXNG
- Evidence, inference, and creative-hypothesis separation
- Five sourced content ideas per research run
- Local script generation through Ollama
- Local scene-plan generation
- Originality-risk and quality review
- PostgreSQL project and pipeline storage
- Manual pipeline stages from Queue to Published
- Manual MiroFish seed export and report import
- Structured synthetic-audience findings
- Local MP4 draft rendering with FFmpeg
- Local speech with eSpeak NG
- SRT subtitle generation from the approved narration
- Manual verified performance and revenue logging
- Node-RED webhook flow for draft production

## Important boundaries

- MiroFish findings are synthetic-agent simulations, not real audience measurements.
- The quality gate is not guaranteed plagiarism detection.
- The first renderer creates useful draft videos with placeholder title cards. Replace them with original or properly licensed visuals before publishing.
- Revenue is never inferred from views.
- Publishing remains manual.
- This version is local single-user software. Do not expose its service ports publicly.

## Architecture

```text
React Studio Control Center
        |
        +-- FastAPI Studio Orchestrator
        |       +-- PostgreSQL
        |       +-- Ollama
        |       +-- SearXNG
        |       +-- MiroFish manual bridge
        |       +-- Local media worker
        |
        +-- Node-RED automation
                +-- quality-approved render webhook
```

## Requirements

- Windows 11, macOS, or Linux
- Docker Desktop
- Git
- 16 GB RAM recommended for `qwen3:8b`
- More RAM or a supported GPU improves local-model speed

## Start on Windows

Clone the repository and switch to the feature branch while the pull request is under review:

```powershell
git clone https://github.com/GRETA1212/blank-app-2.git
cd blank-app-2
git switch feature/local-ai-studio
powershell -ExecutionPolicy Bypass -File .\scripts\start-studio.ps1
```

The startup script:

1. Creates `.env` from the safe template when needed.
2. Builds all containers.
3. Starts PostgreSQL, migrations, SearXNG, Ollama, FastAPI, the React frontend, Node-RED, and the media worker.
4. Downloads the configured Ollama model.
5. Opens the dashboard.

## Service addresses

| Service | Address |
|---|---|
| Studio Control Center | http://localhost:3000 |
| API documentation | http://localhost:8000/docs |
| Node-RED | http://localhost:1880 |
| SearXNG | http://localhost:8080 |
| Ollama | http://localhost:11434 |
| Media worker | http://localhost:9000 |
| PostgreSQL host port | localhost:5433 |

## Stop or inspect

```powershell
.\scripts\status-studio.ps1
.\scripts\stop-studio.ps1
```

Stopping containers does not delete projects, models, or generated media. Those remain in Docker volumes.

## First workflow

1. Open **Research** and enter a focused topic and audience.
2. Review every source and select one idea.
3. Click **Send to Create**.
4. Add your real expertise and generate the script.
5. Edit the title, hook, narration, and description.
6. Generate the scene plan.
7. Run the originality-risk and quality review.
8. Save the project to the pipeline.
9. Use **Render drafts** to generate a local MP4 and SRT.
10. Review the output before moving the project to Published.
11. Enter real platform metrics in Performance.

## Node-RED flow

Import:

```text
automation/node-red/studio-flow.json
```

The flow creates:

```text
POST http://localhost:1880/studio/render
```

Payload:

```json
{
  "project_id": "your-project-uuid"
}
```

The orchestrator still enforces the passing quality-review requirement.

## MiroFish

MiroFish runs separately. This project currently supports the safest first integration:

1. Generate a seed JSON in Audience Simulation.
2. Download or copy it.
3. Run the simulation in your MiroFish installation.
4. Paste the completed report back into the dashboard.
5. Let local AI structure the findings.

Automatic MiroFish submission should only be added after the real backend routes are tested against the installed version.

## Data and media

Docker volumes store:

- PostgreSQL data
- Ollama models
- SearXNG cache
- Node-RED configuration
- Generated MP4/SRT drafts

To permanently remove all local data:

```powershell
docker compose -f docker-compose.local.yml down -v
```

This command is destructive.

## Development

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Orchestrator:

```powershell
cd services/orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.entrypoint:app --reload --port 8000
```

## Validation

GitHub Actions checks:

- Python compilation and FastAPI imports
- React TypeScript production build
- Media-worker compilation
- Docker Compose configuration

## Licensing

See `OPEN_SOURCE_STACK.md`. Application dependencies and AI/media models have separate licences. Verify model, voice, image, and dataset licences before commercial redistribution.
