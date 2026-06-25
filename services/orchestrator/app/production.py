import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from .db import execute_returning, fetch_all, fetch_one, identity

MEDIA_WORKER_URL = os.getenv("MEDIA_WORKER_URL", "http://localhost:9000")
PUBLIC_MEDIA_PREFIX = os.getenv("PUBLIC_MEDIA_PREFIX", "/media").rstrip("/")
router = APIRouter(prefix="/production", tags=["production"])


def serialise(value: Any) -> Any:
    if isinstance(value, list):
        return [serialise(item) for item in value]
    if isinstance(value, dict):
        return {key: serialise(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


@router.get("/jobs")
def list_jobs() -> list[dict[str, Any]]:
    user_id, _ = identity()
    rows = fetch_all(
        "select pj.*, p.title as project_title from production_jobs pj join projects p on p.id = pj.project_id where pj.user_id = %s order by pj.created_at desc",
        (user_id,),
    )
    return serialise(rows)


@router.post("/jobs/{project_id}", status_code=201)
async def render_project(project_id: str) -> dict[str, Any]:
    user_id, _ = identity()
    project = fetch_one("select * from projects where id = %s and user_id = %s", (project_id, user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if (project.get("quality_report") or {}).get("pass") is not True:
        raise HTTPException(status_code=422, detail="A passing quality review is required before rendering")
    if project["status"] == "PUBLISHED":
        raise HTTPException(status_code=422, detail="Duplicate a published project before rendering again")

    job = execute_returning(
        "insert into production_jobs (user_id, project_id, status, started_at) values (%s, %s, 'RUNNING', now()) returning *",
        (user_id, project_id),
    )
    assert job is not None
    execute_returning("update projects set status = 'RENDERING' where id = %s and user_id = %s returning id", (project_id, user_id))

    try:
        async with httpx.AsyncClient(timeout=900) as client:
            response = await client.post(
                f"{MEDIA_WORKER_URL}/render",
                json={
                    "project_id": project_id,
                    "title": project["title"],
                    "narration": project["narration"],
                    "scenes": project.get("scenes") or [],
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
        "notice": "Local draft generated. Human review is required before publishing.",
    }
