from __future__ import annotations

import json
import mimetypes
import os
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from providers.base import ProviderError
from providers.http_client import HttpClient


class YouTubeConnector:
    """YouTube upload and analytics using an authorized-user OAuth token JSON."""

    def __init__(self, token_json: str | None = None) -> None:
        self.token_json = token_json or os.getenv("YOUTUBE_OAUTH_TOKEN_JSON", "")

    @property
    def configured(self) -> bool:
        return bool(self.token_json.strip())

    def _credentials(self):
        if not self.configured:
            raise ProviderError("YOUTUBE_OAUTH_TOKEN_JSON is not configured.")
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as GoogleRequest
        except ImportError as error:
            raise ProviderError("Install Google API dependencies from requirements.txt.") from error
        try:
            info = json.loads(self.token_json)
        except json.JSONDecodeError as error:
            raise ProviderError("YOUTUBE_OAUTH_TOKEN_JSON is invalid JSON.") from error
        credentials = Credentials.from_authorized_user_info(info)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
        if not credentials.valid:
            raise ProviderError("YouTube OAuth credentials are invalid or expired.")
        return credentials

    def upload_video(
        self,
        video_path: Path,
        *,
        title: str,
        description: str,
        tags: list[str] | None = None,
        privacy_status: str = "private",
        category_id: str = "22",
        contains_synthetic_media: bool = True,
    ) -> dict[str, Any]:
        if not video_path.exists():
            raise ProviderError(f"Video not found: {video_path}")
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError as error:
            raise ProviderError("Install Google API dependencies from requirements.txt.") from error
        service = build("youtube", "v3", credentials=self._credentials(), cache_discovery=False)
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": list(tags or [])[:500],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": bool(contains_synthetic_media),
            },
        }
        media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024)
        response = service.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        return {
            "video_id": response.get("id"),
            "url": f"https://www.youtube.com/watch?v={response.get('id')}" if response.get("id") else None,
            "privacy_status": privacy_status,
            "raw": response,
        }

    def analytics(
        self,
        *,
        start_date: date,
        end_date: date,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            from googleapiclient.discovery import build
        except ImportError as error:
            raise ProviderError("Install Google API dependencies from requirements.txt.") from error
        service = build("youtubeAnalytics", "v2", credentials=self._credentials(), cache_discovery=False)
        kwargs: dict[str, Any] = {
            "ids": "channel==MINE",
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained",
            "dimensions": "day",
            "sort": "day",
        }
        if video_id:
            kwargs["filters"] = f"video=={video_id}"
        response = service.reports().query(**kwargs).execute()
        return response


class TikTokDraftConnector:
    """Uploads a local video to the creator inbox for review in TikTok."""

    base_url = "https://open.tiktokapis.com"

    def __init__(self, access_token: str | None = None, http: HttpClient | None = None) -> None:
        self.access_token = access_token or os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self.http = http or HttpClient()

    @property
    def configured(self) -> bool:
        return bool(self.access_token)

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise ProviderError("TIKTOK_ACCESS_TOKEN is not configured.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def upload_draft(self, video_path: Path) -> dict[str, Any]:
        if not video_path.exists():
            raise ProviderError(f"Video not found: {video_path}")
        size = video_path.stat().st_size
        if size <= 0:
            raise ProviderError("Video file is empty.")
        init = self.http.request_json(
            "POST",
            f"{self.base_url}/v2/post/publish/inbox/video/init/",
            headers=self._headers(),
            payload={
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": size,
                    "total_chunk_count": 1,
                }
            },
        )
        error = init.get("error") or {}
        if error.get("code") not in {None, "ok"}:
            raise ProviderError(f"TikTok initialization failed: {error.get('message') or error.get('code')}")
        data = init.get("data") or {}
        upload_url = str(data.get("upload_url", ""))
        publish_id = str(data.get("publish_id", ""))
        if not upload_url or not publish_id:
            raise ProviderError("TikTok did not return upload_url and publish_id.")
        payload = video_path.read_bytes()
        content_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"
        request = Request(
            upload_url,
            data=payload,
            method="PUT",
            headers={
                "Content-Type": content_type,
                "Content-Length": str(size),
                "Content-Range": f"bytes 0-{size - 1}/{size}",
            },
        )
        try:
            with urlopen(request, timeout=600) as response:
                status_code = response.status
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ProviderError(f"TikTok upload HTTP {error.code}: {detail or error.reason}") from error
        except URLError as error:
            raise ProviderError(f"TikTok upload failed: {error.reason}") from error
        if status_code not in {200, 201, 204}:
            raise ProviderError(f"TikTok upload returned HTTP {status_code}.")
        return {"publish_id": publish_id, "status": "UPLOADED_TO_INBOX", "raw": init}

    def get_status(self, publish_id: str) -> dict[str, Any]:
        response = self.http.request_json(
            "POST",
            f"{self.base_url}/v2/post/publish/status/fetch/",
            headers=self._headers(),
            payload={"publish_id": publish_id},
        )
        error = response.get("error") or {}
        if error.get("code") not in {None, "ok"}:
            raise ProviderError(f"TikTok status failed: {error.get('message') or error.get('code')}")
        return response.get("data") or {}


def publication_readiness() -> list[dict[str, Any]]:
    youtube = YouTubeConnector()
    tiktok = TikTokDraftConnector()
    return [
        {
            "platform": "YouTube",
            "configured": youtube.configured,
            "mode": "Private upload first",
            "missing": [] if youtube.configured else ["YOUTUBE_OAUTH_TOKEN_JSON"],
        },
        {
            "platform": "TikTok",
            "configured": tiktok.configured,
            "mode": "Upload to creator inbox for review",
            "missing": [] if tiktok.configured else ["TIKTOK_ACCESS_TOKEN"],
        },
    ]
