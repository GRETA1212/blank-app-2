import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pydantic import BaseModel, Field

from .db import execute, execute_returning, fetch_one, identity

router = APIRouter(prefix="/youtube", tags=["youtube"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8000/youtube/oauth/callback")
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")
MEDIA_OUTPUT_ROOT = Path(os.getenv("MEDIA_OUTPUT_ROOT", "/media-output")).resolve()
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeUploadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=30)
    category_id: str = Field(default="27", pattern=r"^\d+$")


def configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and TOKEN_ENCRYPTION_KEY)


def fernet() -> Fernet:
    if not TOKEN_ENCRYPTION_KEY:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(TOKEN_ENCRYPTION_KEY.encode("utf-8"))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="TOKEN_ENCRYPTION_KEY is invalid") from exc


def client_config() -> dict[str, Any]:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth client credentials are not configured")
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [YOUTUBE_REDIRECT_URI],
        }
    }


def encrypt_credentials(credentials: Credentials) -> str:
    return fernet().encrypt(credentials.to_json().encode("utf-8")).decode("utf-8")


def decrypt_credentials(value: str) -> Credentials:
    try:
        payload = fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        return Credentials.from_authorized_user_info(json.loads(payload), YOUTUBE_SCOPES)
    except (InvalidToken, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Stored YouTube credentials cannot be decrypted") from exc


def connection_for_user(user_id: str) -> dict[str, Any]:
    row = fetch_one(
        "select * from platform_connections where user_id = %s and platform = 'YOUTUBE'",
        (user_id,),
    )
    if row is None:
        raise HTTPException(status_code=409, detail="YouTube is not connected")
    return row


def save_connection(user_id: str, credentials: Credentials, account_id: str | None, account_name: str | None) -> None:
    execute_returning(
        """
        insert into platform_connections (
          user_id, platform, encrypted_credentials, account_id, account_name, scopes, status
        ) values (%s, 'YOUTUBE', %s, %s, %s, %s, 'CONNECTED')
        on conflict (user_id, platform) do update set
          encrypted_credentials = excluded.encrypted_credentials,
          account_id = excluded.account_id,
          account_name = excluded.account_name,
          scopes = excluded.scopes,
          status = 'CONNECTED'
        returning id
        """,
        (
            user_id,
            encrypt_credentials(credentials),
            account_id,
            account_name,
            list(credentials.scopes or YOUTUBE_SCOPES),
        ),
    )


def refreshed_credentials(user_id: str, connection: dict[str, Any]) -> Credentials:
    credentials = decrypt_credentials(connection["encrypted_credentials"])
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        save_connection(user_id, credentials, connection.get("account_id"), connection.get("account_name"))
    if not credentials.valid:
        raise HTTPException(status_code=409, detail="YouTube authorization is expired; reconnect the account")
    return credentials


def media_path_from_url(output_url: str) -> Path:
    prefix = "/media/"
    if not output_url.startswith(prefix):
        raise HTTPException(status_code=500, detail="Production output path is invalid")
    path = (MEDIA_OUTPUT_ROOT / output_url.removeprefix(prefix)).resolve()
    if MEDIA_OUTPUT_ROOT not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Rendered video file is unavailable")
    return path


@router.get("/status")
def youtube_status() -> dict[str, Any]:
    user_id, _ = identity()
    row = fetch_one(
        "select account_id, account_name, scopes, status, updated_at from platform_connections where user_id = %s and platform = 'YOUTUBE'",
        (user_id,),
    )
    return {
        "configured": configured(),
        "connected": bool(row and row["status"] == "CONNECTED"),
        "account_id": row.get("account_id") if row else None,
        "account_name": row.get("account_name") if row else None,
        "status": row.get("status") if row else "DISCONNECTED",
        "updated_at": row["updated_at"].isoformat() if row and row.get("updated_at") else None,
        "upload_policy": "private-only",
    }


@router.get("/oauth/start")
def start_oauth(redirect_after: str = Query(default="http://localhost:3000")) -> dict[str, str]:
    user_id, _ = identity()
    state = secrets.token_urlsafe(32)
    flow = Flow.from_client_config(client_config(), scopes=YOUTUBE_SCOPES, state=state)
    flow.redirect_uri = YOUTUBE_REDIRECT_URI
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    execute("delete from oauth_states where expires_at < now()")
    execute_returning(
        "insert into oauth_states (state, user_id, platform, redirect_after, expires_at) values (%s, %s, 'YOUTUBE', %s, %s) returning state",
        (state, user_id, redirect_after, datetime.now(timezone.utc) + timedelta(minutes=15)),
    )
    return {"authorization_url": authorization_url}


@router.get("/oauth/callback", response_class=HTMLResponse)
def oauth_callback(code: str, state: str) -> HTMLResponse:
    row = fetch_one(
        "select * from oauth_states where state = %s and platform = 'YOUTUBE' and expires_at > now()",
        (state,),
    )
    if row is None:
        raise HTTPException(status_code=400, detail="OAuth state is invalid or expired")
    execute("delete from oauth_states where state = %s", (state,))

    flow = Flow.from_client_config(client_config(), scopes=YOUTUBE_SCOPES, state=state)
    flow.redirect_uri = YOUTUBE_REDIRECT_URI
    flow.fetch_token(code=code)
    credentials = flow.credentials
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    response = youtube.channels().list(part="snippet", mine=True).execute()
    channel = response.get("items", [{}])[0]
    account_id = channel.get("id")
    account_name = channel.get("snippet", {}).get("title")
    save_connection(str(row["user_id"]), credentials, account_id, account_name)
    redirect_after = row.get("redirect_after") or "http://localhost:3000"
    return HTMLResponse(
        f"""<!doctype html><html><body style='font-family:sans-serif;background:#111;color:#eee;padding:40px'>
        <h1>YouTube connected</h1><p>Channel: {account_name or account_id or 'Connected account'}</p>
        <p><a style='color:#d6a84b' href='{redirect_after}'>Return to Studio Control Center</a></p></body></html>"""
    )


@router.delete("/connection", status_code=204)
def disconnect_youtube() -> None:
    user_id, _ = identity()
    execute("delete from platform_connections where user_id = %s and platform = 'YOUTUBE'", (user_id,))


@router.post("/upload/{project_id}", status_code=201)
def upload_private_video(project_id: str, request: YouTubeUploadRequest) -> dict[str, Any]:
    user_id, _ = identity()
    project = fetch_one("select * from projects where id = %s and user_id = %s", (project_id, user_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    approval = fetch_one(
        "select status from approval_reviews where project_id = %s and user_id = %s",
        (project_id, user_id),
    )
    if approval is None or approval["status"] != "APPROVED":
        raise HTTPException(status_code=422, detail="Explicit human approval is required before YouTube upload")
    job = fetch_one(
        "select * from production_jobs where project_id = %s and user_id = %s and status = 'COMPLETED' order by completed_at desc limit 1",
        (project_id, user_id),
    )
    if job is None or not job.get("output_url"):
        raise HTTPException(status_code=422, detail="A completed rendered draft is required")

    connection = connection_for_user(user_id)
    credentials = refreshed_credentials(user_id, connection)
    video_path = media_path_from_url(job["output_url"])
    title = (request.title or project["title"])[:100]
    description = (request.description if request.description is not None else project["description"])[:5000]

    upload_row = execute_returning(
        """
        insert into platform_uploads (
          user_id, project_id, production_job_id, platform, status,
          privacy_status, upload_title, upload_description
        ) values (%s, %s, %s, 'YOUTUBE', 'UPLOADING', 'private', %s, %s)
        returning *
        """,
        (user_id, project_id, job["id"], title, description),
    )
    assert upload_row is not None

    try:
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
        response = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": request.tags[:30],
                    "categoryId": request.category_id,
                },
                "status": {
                    "privacyStatus": "private",
                    "selfDeclaredMadeForKids": False,
                },
            },
            media_body=media,
        ).execute()
    except Exception as exc:
        execute_returning(
            "update platform_uploads set status = 'FAILED', error_message = %s, completed_at = now() where id = %s returning id",
            (str(exc)[:4000], upload_row["id"]),
        )
        raise HTTPException(status_code=502, detail="YouTube upload failed") from exc

    video_id = response.get("id")
    completed = execute_returning(
        """
        update platform_uploads set status = 'COMPLETED', external_id = %s,
          external_url = %s, completed_at = now()
        where id = %s returning *
        """,
        (video_id, f"https://studio.youtube.com/video/{video_id}/edit" if video_id else None, upload_row["id"]),
    )
    assert completed is not None
    return {
        "id": str(completed["id"]),
        "status": completed["status"],
        "video_id": video_id,
        "studio_url": completed.get("external_url"),
        "privacy_status": "private",
        "notice": "Uploaded privately. Review in YouTube Studio before changing visibility.",
    }
