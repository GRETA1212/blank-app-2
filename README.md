# Studio Control Center

A local-first control center for researching, creating, reviewing, translating, rendering, and tracking YouTube/TikTok content.

The system runs on your own computer with open-source or locally hosted services, so there is no mandatory per-request AI subscription.

## What works

- Current public-web research through self-hosted SearXNG
- Evidence, inference, and creative-hypothesis separation
- Five sourced content ideas per research run
- Local script and scene-plan generation through Ollama
- Originality-risk and quality review
- PostgreSQL project and pipeline storage
- English, Italian, Albanian, and Macedonian content variants
- Separate human approval for every language
- Piper neural voice installation and preview
- Macedonian eSpeak NG fallback
- Voice speed control
- faster-whisper transcription of the generated audio
- Timestamped SRT subtitles built from the actual audio
- Transcript-to-script similarity checks
- Local FFmpeg MP4 rendering
- Asset-rights tracking and approval review
- Manual MiroFish seed export and report import
- Manual verified performance and revenue logging
- Node-RED webhook flow for draft production

## Important boundaries

- Generated translations require human linguistic and factual review.
- Transcript matching is a quality-control aid, not a pronunciation guarantee.
- Piper voice models have separate model cards and licences; review them before commercial distribution.
- MiroFish findings are synthetic-agent simulations, not real audience measurements.
- The quality gate is not guaranteed plagiarism detection.
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
        |       +-- Language variants
        |       +-- MiroFish manual bridge
        |       +-- Media worker
        |              +-- Piper / eSpeak
        |              +-- faster-whisper
        |              +-- FFmpeg
        |
        +-- Node-RED automation
```

## Requirements

- Windows 11, macOS, or Linux
- Docker Desktop
- Git
- 16 GB RAM recommended for `qwen3:8b`
- More RAM or a supported GPU improves local-model and transcription speed

## Start on Windows

```powershell
git clone https://github.com/GRETA1212/blank-app-2.git
cd blank-app-2
git switch feature/local-ai-studio
powershell -ExecutionPolicy Bypass -File .\scripts\start-studio.ps1
```

The startup script creates `.env`, builds the containers, starts all services, downloads the configured Ollama model, and opens the dashboard.

On first use, configured Piper voices and the selected Whisper model may also download. These files remain in Docker volumes for later runs.

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

Stopping containers does not delete projects, models, voices, transcripts, or generated media.

## Main workflow

1. Open **Research** and enter a focused topic and audience.
2. Review the sources and send one idea to **Create**.
3. Add your real expertise and generate the script.
4. Edit the title, hook, narration, description, and scenes.
5. Run the originality-risk and quality review.
6. Save the project to the pipeline.
7. Open **Languages** to generate English, Italian, Albanian, and Macedonian variants.
8. Review and approve each language separately.
9. Open **Audio studio**.
10. Choose the master or an approved language variant.
11. Install or preview the selected local voice.
12. Render the MP4. Whisper transcribes the actual audio and generates the SRT.
13. Review the transcript similarity report, subtitles, audio, visuals, rights, and disclosures.
14. Publish manually and enter verified metrics in Performance.

## Language and audio configuration

```env
PIPER_AUTO_DOWNLOAD=true
PIPER_AUTO_VOICES=en_US-lessac-medium,it_IT-paola-medium,sq_AL-edon-medium
PIPER_DEFAULT_VOICE=en_US-lessac-medium
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
SUBTITLE_VERIFY_THRESHOLD=0.82
```

See `docs/AUDIO_LANGUAGES.md` for the detailed language, voice, and transcript workflow.

## Node-RED flow

Import:

```text
automation/node-red/studio-flow.json
```

The flow exposes:

```text
POST http://localhost:1880/studio/render
```

Payload:

```json
{
  "project_id": "your-project-uuid"
}
```

The orchestrator still enforces the quality-review requirement.

## MiroFish

MiroFish runs separately. The current safe integration is:

1. Generate a seed JSON in Audience Simulation.
2. Run it in the installed MiroFish application.
3. Paste the completed report back into the dashboard.
4. Let local AI structure the findings.

Automatic submission is not claimed until the installed backend routes are tested.

## Persistent data

Docker volumes store:

- PostgreSQL data
- Ollama models
- Piper voices
- Whisper models
- SearXNG cache
- Node-RED configuration
- generated audio, transcripts, subtitles, and videos

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

GitHub Actions checks Python compilation/imports, unit tests, the React TypeScript production build, and Docker Compose configuration.

## Licensing

See `OPEN_SOURCE_STACK.md`. Application dependencies, AI models, voice models, images, and datasets have separate licences that must be reviewed before commercial redistribution.
