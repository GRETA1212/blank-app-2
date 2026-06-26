# Approved Open-Source Stack

This project intentionally prefers reusable open-source components over proprietary monthly services.

## Frontend

- React + TypeScript + Vite
- Tailwind CSS — MIT
- React Flow / xyflow — MIT
- TanStack Query — MIT
- Zod — MIT
- Lucide icons — ISC

## Backend and agents

- FastAPI — MIT
- Ollama — MIT
- PostgreSQL — PostgreSQL License

## Search and automation

- SearXNG — AGPL-3.0; run as a separate service and preserve its source/licence obligations
- Node-RED — Apache-2.0

## Simulation

- MiroFish — AGPL-3.0; run as a separate service rather than copying its source into the application

## Media pipeline

- FFmpeg — LGPL/GPL depending on build configuration
- Piper engine (`piper-tts`) — GPL-3.0
- Piper voice models — each model has its own model card and licence; review before commercial distribution
- faster-whisper — MIT
- Whisper model weights — MIT
- eSpeak NG fallback — GPL-3.0
- Pillow — HPND

## Licensing rules

1. Keep all upstream LICENSE and NOTICE files required by each dependency.
2. Do not copy code from a repository that has no explicit licence.
3. Keep AGPL services isolated and publish modifications when the licence requires it.
4. Verify model and dataset licences separately from application-code licences.
5. Do not describe source-available software as open source unless its licence is OSI-compatible.
6. Before commercial distribution, run an automated dependency-licence audit and review this file.
