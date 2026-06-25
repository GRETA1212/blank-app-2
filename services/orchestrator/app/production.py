import os
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .db import execute_returning, fetch_all, fetch_one, identity

MEDIA_WORKER_URL = os.getenv("MEDIA_WORKER_URL", "http://localhost:9000")
PUBLIC_MEDIA_PREFIX = os.getenv("PUBLIC_MEDIA_PREFIX", "/media").rstrip("/")
router = APIRouter(prefix="/production", tags=["production"])


class RenderOptions(BaseModel):
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    voice_id: str | None = None
    burn_subtitles: bool = True


class VoicePreview(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    voice_id: str | None = None


class ShortsOptions(BaseModel):
    count: int = Field(default=3, ge=1, le=5)
    duration_seconds: int = Field(default=45, ge=15, le=60)


def serialise(value: Any) -> Any:
    if isinstance(value, list):
        return [serialise(item) for item in value]
    if isinstance(value, dict):
        return {key: serialise(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def enrich_scenes(scenes: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for scene in scenes:
        item = dict(scene)
        asset_id = item.get("asset_id")
        if asset_id:
            asset = fetch_one("select * from media_assets where id = %s and user_id = %s", (asset_id, user_id))
            if asset is None:
                raise HTTPException(status_code=422, detail=f"Scene {item.get('scene_number')} asset was not found")
            if asset["license_status"] == "UNKNOWN":
                raise HTTPException(status_code=422, detail=f"Scene {item.get('scene_number')} asset licence must be verified")
            if asset["media_type"] not in {"IMAGE", "VIDEO"}:
                raise HTTPException(status_code=422, detail=f"Scene {item.get('scene_number')} requires an image or video asset")
            item["asset_path"] = asset["storage_path"]
            item["asset_media_type"] = asset["media_type"]
        enriched.append(item)
    return enriched


@router.get("/jobs")
def list_jobs() -> list[dict[str, Any]]:
    user_id, _ = identity()
    rows = fetch_all(
        "select pj.*, p.title as project_title from production_jobs pj join projects p on p.id = pj.project_id where pj.user_id = %s order by pj.created_at desc",
        (user_id,),
    )
    return serialise(rows)


@router.get("/derivatives")
def list_derivatives(project_id: str | None = None) -> list[dict[str, Any]]:
    user_id, _ = identity()
    if project_id:
        rows = fetch_all("select * from content_derivatives where user_id = %s and project_id = %s order by created_at desc", (user_id, project_id))
    else:
        rows = fetch_all("select * from content_derivatives where user_id = %s order by created_at desc", (user_id,))
    return serialise(rows)


@router.get("/voices")
async def list_voices() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{MEDIA_WORKER_URL}/voices")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Voice service is unavailable") from exc


@router.post("/voice-preview")
async def preview_voice(request: VoicePreview) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(f"{MEDIA_WORKER_URL}/voice-preview", json=request.model_dump())
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Voice preview failed") from exc
    return {
        **result,
        "audio_url": f"{PUBLIC_MEDIA_PREFIX}/{result['audio_path']}",
    }


@router.post("/jobs/{project_id}", status_code=201)
async def render_project(project_id: str, options: RenderOptions = RenderOptions()) -> dict[str, Any]:
    user_id, _ = identity()
    project = fetch_one("select * from projects where id = %s and user_id = %s", (project_id, user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if (project.get("quality_report") or {}).get("pass") is not True:
        raise HTTPException(status_code=422, detail="A passing quality review is required before rendering")
    if project["status"] == "PUBLISHED":
        raise HTTPException(status_code=422, detail="Duplicate a published project before rendering again")

    scenes = enrich_scenes(project.get("scenes") or [], user_id)
    job = execute_returning(
        "insert into production_jobs (user_id, project_id, status, started_at) values (%s, %s, 'RUNNING', now()) returning *",
        (user_id, project_id),
    )
    assert job is not None
    execute_returning("update projects set status = 'RENDERING' where id = %s and user_id = %s returning id", (project_id, user_id))

    try:
        async with httpx.AsyncClient(timeout=1800) as client:
            response = await client.post(
                f"{MEDIA_WORKER_URL}/render",
                json={
                    "project_id": project_id,
                    "title": project["title"],
                    "narration": project["narration"],
                    "scenes": scenes,
                    **options.model_dump(),
                },
            )
            response.raise_for_status()
            rendered = response.json()
    except httpx.HTTPError as exc:
        error = str(exc)[:4000]
        execute_returning("update production_jobs set status = 'FAILED', error_message = %s, completed_at = now() where id = %s returning id", (error, job["id"]))
        execute_returning("update projects set status = 'IN_PRODUCTION' where id = %s and user_id = %s returning id", (project_id, user_id))
        raise HTTPException(status_code=502, detail="Local rendering failed") from exc

    output_url = f"{PUBLIC_MEDIA_PREFIX}/{rendered['video_path']}"
    subtitle_url = f"{PUBLIC_MEDIA_PREFIX}/{rendered['subtitle_path']}"
    completed = execute_returning(
        "update production_jobs set status = 'COMPLETED', output_url = %s, subtitle_url = %s, completed_at = now() where id = %s returning *",
        (output_url, subtitle_url, job["id"]),
    )
    execute_returning("update projects set status = 'REVIEW' where id = %s and user_id = %s returning id", (project_id, user_id))
    assert completed is not None
    return {
        **serialise(completed),
        "renderer": rendered,
        "notice": "Draft generated. Complete the factual, rights, audio, visual, subtitle, and disclosure review before upload.",
    }


@router.post("/jobs/{job_id}/shorts", status_code=201)
async def generate_shorts(job_id: str, options: ShortsOptions) -> dict[str, Any]:
    user_id, _ = identity()
    job = fetch_one("select * from production_jobs where id = %s and user_id = %s", (job_id, user_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Production job not found")
    if job["status"] != "COMPLETED" or not job.get("output_url"):
        raise HTTPException(status_code=422, detail="A completed draft is required")
    relative = job["output_url"].removeprefix(f"{PUBLIC_MEDIA_PREFIX}/")
    try:
        async with httpx.AsyncClient(timeout=1800) as client:
            response = await client.post(
                f"{MEDIA_WORKER_URL}/shorts",
                json={"source_relative_path": relative, **options.model_dump()},
            )
            response.raise_for_status()
            rendered = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Short-form generation failed") from exc

    outputs: list[dict[str, Any]] = []
    for index, path in enumerate(rendered.get("outputs", []), start=1):
        url = f"{PUBLIC_MEDIA_PREFIX}/{path}"
        row = execute_returning(
            """
            insert into content_derivatives (
              user_id, project_id, production_job_id, kind, variant_label,
              status, output_url, completed_at
            ) values (%s, %s, %s, 'SHORT', %s, 'COMPLETED', %s, now())
            returning *
            """,
            (user_id, job["project_id"], job["id"], f"Short {index}", url),
        )
        if row:
            outputs.append(serialise(row))
    return {"derivatives": outputs, "renderer": rendered}
