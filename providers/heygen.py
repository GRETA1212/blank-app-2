from __future__ import annotations

import os

from .base import JobStatus, ProviderError, ProviderJob, VideoRequest
from .http_client import HttpClient


class HeyGenVideoProvider:
    """Generate talking shots from an authorized HeyGen avatar."""

    name = "heygen"
    base_url = "https://api.heygen.com/v3"

    def __init__(
        self,
        api_key: str | None = None,
        default_avatar_id: str | None = None,
        default_voice_id: str | None = None,
        default_engine: str | None = None,
        http: HttpClient | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY", "")
        self.default_avatar_id = default_avatar_id or os.getenv("HEYGEN_AVATAR_ID", "")
        self.default_voice_id = default_voice_id or os.getenv("HEYGEN_VOICE_ID", "")
        self.default_engine = default_engine or os.getenv("HEYGEN_ENGINE", "avatar_v")
        self.http = http or HttpClient()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.default_avatar_id and self.default_voice_id)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderError("HEYGEN_API_KEY is not configured.")
        return {"x-api-key": self.api_key, "Content-Type": "application/json"}

    def create_video(self, request: VideoRequest) -> ProviderJob:
        avatar_id = request.avatar_id or self.default_avatar_id
        voice_id = request.voice_id or self.default_voice_id
        if not avatar_id:
            raise ProviderError("An authorized HeyGen avatar ID is required.")
        if not voice_id and not request.audio_url:
            raise ProviderError("An authorized HeyGen voice ID or audio URL is required.")
        if not request.script and not request.audio_url:
            raise ProviderError("HeyGen requires either a script or authorized audio.")

        payload: dict[str, object] = {
            "type": "avatar",
            "avatar_id": avatar_id,
            "title": request.title or f"{request.project_id} shot {request.shot_number}",
            "aspect_ratio": request.aspect_ratio,
            "resolution": "1080p",
            "motion_prompt": request.prompt[:500],
        }
        if self.default_engine:
            payload["engine"] = {"type": self.default_engine}
        if request.audio_url:
            if not request.audio_url.startswith("https://"):
                raise ProviderError("HeyGen audio URLs must use HTTPS.")
            payload["audio_url"] = request.audio_url
        else:
            payload["script"] = request.script or ""
            payload["voice_id"] = voice_id

        data = self.http.request_json("POST", f"{self.base_url}/videos", headers=self._headers(), payload=payload)
        response_data = data.get("data") or {}
        job_id = str(response_data.get("video_id", ""))
        if not job_id:
            raise ProviderError("HeyGen did not return a video ID.")
        raw_status = str(response_data.get("status", "pending")).lower()
        status = JobStatus.PROCESSING if raw_status == "processing" else JobStatus.QUEUED
        return ProviderJob(provider=self.name, job_id=job_id, status=status, raw=data)

    def get_job(self, job_id: str) -> ProviderJob:
        data = self.http.request_json("GET", f"{self.base_url}/videos/{job_id}", headers=self._headers())
        response_data = data.get("data") or {}
        raw_status = str(response_data.get("status", "processing")).lower()
        if raw_status == "completed":
            status = JobStatus.SUCCEEDED
        elif raw_status == "failed":
            status = JobStatus.FAILED
        elif raw_status == "pending":
            status = JobStatus.QUEUED
        else:
            status = JobStatus.PROCESSING
        output_url = response_data.get("video_url") if status is JobStatus.SUCCEEDED else None
        error = None
        if status is JobStatus.FAILED:
            error = str(response_data.get("failure_message") or response_data.get("failure_code") or "HeyGen generation failed.")
        return ProviderJob(provider=self.name, job_id=job_id, status=status, output_url=output_url, error=error, raw=data)
