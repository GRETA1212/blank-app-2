from __future__ import annotations

import os

from .base import JobStatus, ProviderError, ProviderJob, VideoRequest
from .http_client import HttpClient


class RunwayVideoProvider:
    """Generate authorized fictional-character shots from approved reference images."""

    name = "runway"
    base_url = "https://api.dev.runwayml.com/v1"
    api_version = "2024-11-06"

    def __init__(self, api_key: str | None = None, default_model: str | None = None, http: HttpClient | None = None) -> None:
        self.api_key = api_key or os.getenv("RUNWAYML_API_SECRET", "")
        self.default_model = default_model or os.getenv("RUNWAY_MODEL", "gen4_turbo")
        self.http = http or HttpClient()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderError("RUNWAYML_API_SECRET is not configured.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Version": self.api_version,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _ratio(aspect_ratio: str) -> str:
        return {"9:16": "720:1280", "16:9": "1280:720", "1:1": "960:960"}.get(aspect_ratio, "720:1280")

    def create_video(self, request: VideoRequest) -> ProviderJob:
        if not request.reference_image_url:
            raise ProviderError("Runway image-to-video requires an approved HTTPS reference image URL.")
        if not request.reference_image_url.startswith("https://"):
            raise ProviderError("Runway reference images must use HTTPS.")
        duration = int(request.duration_seconds)
        if duration not in {5, 10}:
            duration = 5 if duration < 8 else 10

        data = self.http.request_json(
            "POST",
            f"{self.base_url}/image_to_video",
            headers=self._headers(),
            payload={
                "model": request.model or self.default_model,
                "promptImage": request.reference_image_url,
                "promptText": request.prompt[:1000],
                "duration": duration,
                "ratio": self._ratio(request.aspect_ratio),
            },
        )
        job_id = str(data.get("id", ""))
        if not job_id:
            raise ProviderError("Runway did not return a task ID.")
        return ProviderJob(provider=self.name, job_id=job_id, status=JobStatus.QUEUED, raw=data)

    def get_job(self, job_id: str) -> ProviderJob:
        data = self.http.request_json("GET", f"{self.base_url}/tasks/{job_id}", headers=self._headers())
        raw_status = str(data.get("status", "")).upper()
        status = {
            "PENDING": JobStatus.QUEUED,
            "THROTTLED": JobStatus.QUEUED,
            "RUNNING": JobStatus.PROCESSING,
            "SUCCEEDED": JobStatus.SUCCEEDED,
            "FAILED": JobStatus.FAILED,
            "CANCELED": JobStatus.FAILED,
        }.get(raw_status, JobStatus.PROCESSING)
        output = data.get("output") or []
        output_url = output[0] if status is JobStatus.SUCCEEDED and output else None
        error = None
        if status is JobStatus.FAILED:
            error = str(data.get("failure") or data.get("failureCode") or "Runway generation failed.")
        return ProviderJob(provider=self.name, job_id=job_id, status=status, output_url=output_url, error=error, raw=data)
