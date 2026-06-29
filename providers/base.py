from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Raised when an external media provider rejects or fails a request."""


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class VideoRequest:
    project_id: str
    shot_number: int
    prompt: str
    duration_seconds: int
    aspect_ratio: str = "9:16"
    title: str = ""
    script: str | None = None
    avatar_id: str | None = None
    voice_id: str | None = None
    audio_url: str | None = None
    reference_image_url: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceRequest:
    text: str
    voice_id: str | None = None
    model_id: str | None = None
    output_format: str = "mp3_44100_128"
    stability: float = 0.5
    similarity_boost: float = 0.8
    style: float = 0.25
    speed: float = 1.0


@dataclass
class ProviderJob:
    provider: str
    job_id: str
    status: JobStatus
    output_url: str | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class VideoProvider(Protocol):
    name: str

    def create_video(self, request: VideoRequest) -> ProviderJob:
        ...

    def get_job(self, job_id: str) -> ProviderJob:
        ...


class VoiceProvider(Protocol):
    name: str

    def synthesize(self, request: VoiceRequest, output_path: Path) -> Path:
        ...
