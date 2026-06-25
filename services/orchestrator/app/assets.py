import mimetypes
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .db import execute, execute_returning, fetch_all, fetch_one, identity

ASSET_ROOT = Path(os.getenv("ASSET_ROOT", "/studio-assets")).resolve()
ASSET_ROOT.mkdir(parents=True, exist_ok=True)
MAX_ASSET_BYTES = int(os.getenv("MAX_ASSET_BYTES", str(500 * 1024 * 1024)))

router = APIRouter(prefix="/assets", tags=["assets"])

ALLOWED_LICENSES = {"OWNED", "LICENSED", "PUBLIC_DOMAIN", "UNKNOWN"}
ALLOWED_MEDIA = {
    "image/": "IMAGE",
    "video/": "VIDEO",
    "audio/": "AUDIO",
    "application/pdf": "DOCUMENT",
}


def serialise(value: Any) -> Any:
    if isinstance(value, list):
        return [serialise(item) for item in value]
    if isinstance(value, dict):
        return {key: serialise(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def safe_name(value: str) -> str:
    stem = Path(value).stem
    suffix = Path(value).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._") or "asset"
    return f"{stem[:80]}{suffix[:12]}"


def classify_media(mime_type: str) -> str:
    for prefix, media_type in ALLOWED_MEDIA.items():
        if mime_type == prefix or mime_type.startswith(prefix):
            return media_type
    raise HTTPException(status_code=415, detail="Unsupported media type")


@router.get("")
def list_assets(project_id: str | None = None) -> list[dict[str, Any]]:
    user_id, workspace_id = identity()
    if project_id:
        rows = fetch_all(
            "select * from media_assets where user_id = %s and workspace_id = %s and project_id = %s order by created_at desc",
            (user_id, workspace_id, project_id),
        )
    else:
        rows = fetch_all(
            "select * from media_assets where user_id = %s and workspace_id = %s order by created_at desc",
            (user_id, workspace_id),
        )
    return serialise(rows)


@router.post("", status_code=201)
async def upload_asset(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    license_status: str = Form(default="UNKNOWN"),
    license_source: str = Form(default=""),
    attribution: str = Form(default=""),
    notes: str = Form(default=""),
) -> dict[str, Any]:
    user_id, workspace_id = identity()
    license_status = license_status.upper()
    if license_status not in ALLOWED_LICENSES:
        raise HTTPException(status_code=422, detail="Invalid licence status")
    if project_id:
        project = fetch_one("select id from projects where id = %s and user_id = %s", (project_id, user_id))
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

    original_name = file.filename or "asset"
    mime_type = file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
    media_type = classify_media(mime_type)
    stored_name = f"{uuid4().hex}-{safe_name(original_name)}"
    destination = (ASSET_ROOT / stored_name).resolve()
    if ASSET_ROOT not in destination.parents:
        raise HTTPException(status_code=400, detail="Invalid asset path")

    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_ASSET_BYTES:
                    raise HTTPException(status_code=413, detail="Asset exceeds local size limit")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    row = execute_returning(
        """
        insert into media_assets (
          user_id, workspace_id, project_id, file_name, stored_name, media_type,
          mime_type, file_size, storage_path, public_url, license_status,
          license_source, attribution, notes
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning *
        """,
        (
            user_id,
            workspace_id,
            project_id,
            original_name,
            stored_name,
            media_type,
            mime_type,
            size,
            str(destination),
            f"/assets/files/{stored_name}",
            license_status,
            license_source,
            attribution,
            notes,
        ),
    )
    assert row is not None
    return serialise(row)


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: str) -> None:
    user_id, _ = identity()
    row = fetch_one("select storage_path from media_assets where id = %s and user_id = %s", (asset_id, user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    deleted = execute("delete from media_assets where id = %s and user_id = %s", (asset_id, user_id))
    if deleted:
        Path(row["storage_path"]).unlink(missing_ok=True)
