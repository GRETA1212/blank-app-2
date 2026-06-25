# Approved Open-Source Stack

This project intentionally prefers reusable open-source components over proprietary monthly services.

## Frontend

- React + TypeScript + Vite
- shadcn/ui patterns and components — MIT
- Tailwind CSS — MIT
- React Flow / xyflow — MIT
- TanStack Query — MIT
- Zod — MIT
- Lucide icons — ISC

## Backend and agents

- FastAPI — MIT
- LangGraph — MIT
- Ollama — MIT
- PostgreSQL — PostgreSQL License

## Search and automation

- SearXNG — AGPL-3.0; run as a separate service and preserve its source/license obligations
- Node-RED — Apache-2.0

## Simulation

- MiroFish — AGPL-3.0; run as a separate service rather than copying its source into the application

## Media pipeline

- FFmpeg — LGPL/GPL depending on build configuration
- faster-whisper — MIT
- Piper-compatible local TTS — verify the specific repository/model license before distribution
- ComfyUI — GPL-3.0

## Licensing rules

1. Keep all upstream LICENSE and NOTICE files required by each dependency.
2. Do not copy code from a repository that has no explicit license.
3. Keep AGPL services isolated and publish modifications when the license requires it.
4. Verify model and dataset licenses separately from application-code licenses.
5. Do not describe source-available software as open source unless its license is OSI-compatible.
6. Before commercial distribution, run an automated dependency-license audit and review this file.
