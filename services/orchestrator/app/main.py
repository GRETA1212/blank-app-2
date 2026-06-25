import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Studio Orchestrator", version="0.1.0")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
MIROFISH_BASE_URL = os.getenv("MIROFISH_BASE_URL", "http://localhost:5001")


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=20000)
    system: str = Field(default="You are a careful content studio assistant.", max_length=5000)
    temperature: float = Field(default=0.4, ge=0, le=1.5)


class GenerateResponse(BaseModel):
    model: str
    content: str


class MiroFishSeedRequest(BaseModel):
    project_id: str
    topic: str
    audience: dict[str, Any]
    content_variants: list[dict[str, Any]]
    simulation_question: str
    research_context: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "ok",
        "ollama": False,
        "mirofish": False,
        "model": OLLAMA_MODEL,
    }
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            result["ollama"] = response.is_success
        except httpx.HTTPError:
            pass
        try:
            response = await client.get(MIROFISH_BASE_URL)
            result["mirofish"] = response.status_code < 500
        except httpx.HTTPError:
            pass
    return result


@app.post("/ai/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": request.system},
            {"role": "user", "content": request.prompt},
        ],
        "options": {"temperature": request.temperature},
    }
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Local AI service is unavailable") from exc

    data = response.json()
    content = data.get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=502, detail="Local AI returned an invalid response")
    return GenerateResponse(model=OLLAMA_MODEL, content=content.strip())


@app.post("/mirofish/seed")
async def build_mirofish_seed(request: MiroFishSeedRequest) -> dict[str, Any]:
    return {
        "version": "1.0",
        "project_id": request.project_id,
        "research_context": request.research_context,
        "audience": request.audience,
        "content_variants": request.content_variants,
        "simulation_question": request.simulation_question,
        "requested_outputs": [
            "audience_segment_reactions",
            "hook_comparison",
            "objections",
            "confusing_sections",
            "trust_risks",
            "predicted_comments",
            "recommended_changes",
        ],
        "disclaimer": "Synthetic audience simulation only; not real audience measurement or guaranteed performance.",
    }
