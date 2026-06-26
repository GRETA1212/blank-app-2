import os
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

MEDIA_WORKER_URL = os.getenv("MEDIA_WORKER_URL", "http://localhost:9000")
PUBLIC_MEDIA_PREFIX = os.getenv("PUBLIC_MEDIA_PREFIX", "/media").rstrip("/")
router = APIRouter(prefix="/production/audio", tags=["production-audio"])


class AudioPreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language_code: Literal["en", "it", "sq", "mk"] = "en"
    voice_id: str | None = None
    speed: float = Field(default=1.0, ge=0.65, le=1.5)


@router.get("/voices")
async def voices(language_code: str | None = None) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{MEDIA_WORKER_URL}/audio/voices",
                params={"language_code": language_code} if language_code else None,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Enhanced voice service is unavailable") from exc


@router.post("/voices/{voice_id}/install")
async def install_voice(voice_id: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=1200) as client:
            response = await client.post(f"{MEDIA_WORKER_URL}/audio/voices/{voice_id}/install")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Neural voice installation failed") from exc


@router.post("/voice-preview")
async def preview_voice(request: AudioPreviewRequest) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=600) as client:
            response = await client.post(
                f"{MEDIA_WORKER_URL}/audio/voice-preview",
                json=request.model_dump(),
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Voice preview failed") from exc
    return {**result, "audio_url": f"{PUBLIC_MEDIA_PREFIX}/{result['audio_path']}"}
