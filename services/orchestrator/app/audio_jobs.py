import os
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .db import execute_returning, fetch_one, identity
from .production import enrich_scenes, serialise

MEDIA_WORKER_URL = os.getenv("MEDIA_WORKER_URL", "http://localhost:9000")
PUBLIC_MEDIA_PREFIX = os.getenv("PUBLIC_MEDIA_PREFIX", "/media").rstrip("/")
router = APIRouter(prefix="/production/audio", tags=["production-audio"])


class AudioRenderOptions(BaseModel):
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    content_variant_id: str | None = None
    language_code: Literal["en", "it", "sq", "mk"] | None = None
    voice_id: str | None = None
    voice_speed: float = Field(default=1.0, ge=0.65, le=1.5)
    burn_subtitles: bool = True
    verify_subtitles: bool = True


@router.post("/jobs/{project_id}", status_code=201)
async def render_audio_job(project_id: str, options: AudioRenderOptions) -> dict:
    user_id, _ = identity()
    project = fetch_one("select * from projects where id = %s and user_id = %s", (project_id, user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if (project.get("quality_report") or {}).get("pass") is not True:
        raise HTTPException(status_code=422, detail="A passing quality review is required")
    if project["status"] == "PUBLISHED":
        raise HTTPException(status_code=422, detail="Duplicate a published project before rendering")

    variant = None
    if options.content_variant_id:
        variant = fetch_one(
            "select * from content_variants where id = %s and project_id = %s and user_id = %s",
            (options.content_variant_id, project_id, user_id),
        )
        if variant is None:
            raise HTTPException(status_code=404, detail="Localized variant not found")
        if variant["review_status"] != "APPROVED":
            raise HTTPException(status_code=422, detail="Approve the localized variant before rendering")

    content = variant or project
    language_code = (variant or {}).get("language_code") or options.language_code or "en"
    voice_id = options.voice_id or (variant or {}).get("voice_id")
    scenes = enrich_scenes(content.get("scenes") or [], user_id)
    job = execute_returning(
        """
        insert into production_jobs (
          user_id, project_id, content_variant_id, language_code, voice_id, status, started_at
        ) values (%s, %s, %s, %s, %s, 'RUNNING', now()) returning *
        """,
        (user_id, project_id, options.content_variant_id, language_code, voice_id),
    )
    assert job is not None
    execute_returning("update projects set status = 'RENDERING' where id = %s and user_id = %s returning id", (project_id, user_id))

    try:
        async with httpx.AsyncClient(timeout=3600) as client:
            response = await client.post(
                f"{MEDIA_WORKER_URL}/render-v2",
                json={
                    "project_id": project_id,
                    "title": content["title"],
                    "narration": content["narration"],
                    "scenes": scenes,
                    "aspect_ratio": options.aspect_ratio,
                    "language_code": language_code,
                    "voice_id": voice_id,
                    "voice_speed": options.voice_speed,
                    "burn_subtitles": options.burn_subtitles,
                    "verify_subtitles": options.verify_subtitles,
                },
            )
            response.raise_for_status()
            rendered = response.json()
    except httpx.HTTPError as exc:
        execute_returning("update production_jobs set status = 'FAILED', error_message = %s, completed_at = now() where id = %s returning id", (str(exc)[:4000], job["id"]))
        execute_returning("update projects set status = 'IN_PRODUCTION' where id = %s and user_id = %s returning id", (project_id, user_id))
        raise HTTPException(status_code=502, detail="Enhanced local rendering failed") from exc

    output_url = f"{PUBLIC_MEDIA_PREFIX}/{rendered['video_path']}"
    subtitle_url = f"{PUBLIC_MEDIA_PREFIX}/{rendered['subtitle_path']}"
    transcript_url = f"{PUBLIC_MEDIA_PREFIX}/{rendered['transcript_path']}"
    completed = execute_returning(
        """
        update production_jobs set status = 'COMPLETED', output_url = %s, subtitle_url = %s,
          transcript_url = %s, voice_id = %s, voice_engine = %s,
          subtitle_verification = %s, language_code = %s, completed_at = now()
        where id = %s returning *
        """,
        (output_url, subtitle_url, transcript_url, rendered.get("voice_id"), rendered.get("voice_engine"), Jsonb(rendered.get("subtitle_verification") or {}), language_code, job["id"]),
    )
    execute_returning("update projects set status = 'REVIEW' where id = %s and user_id = %s returning id", (project_id, user_id))
    assert completed is not None
    return {
        **serialise(completed),
        "renderer": rendered,
        "notice": "Human translation, audio, transcript, subtitle, factual, visual, rights, and disclosure review is required.",
    }
