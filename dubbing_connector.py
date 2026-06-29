from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class DubbingError(RuntimeError):
    pass


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return {"value": str(value)}


class ElevenLabsDubbing:
    """Thin wrapper around ElevenLabs' official Python SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _client(self):
        if not self.api_key:
            raise DubbingError("ELEVENLABS_API_KEY is not configured.")
        try:
            from elevenlabs import ElevenLabs
        except ImportError as error:  # pragma: no cover
            raise DubbingError("Install the official elevenlabs Python package.") from error
        return ElevenLabs(api_key=self.api_key)

    def create(
        self,
        *,
        source_url: str,
        target_lang: str,
        source_lang: str = "en",
        name: str = "Virtual Creator Dub",
        num_speakers: int = 1,
        watermark: bool = False,
        disable_voice_cloning: bool = True,
    ) -> dict[str, Any]:
        if not source_url.startswith("https://"):
            raise ValueError("Dubbing source_url must be a public or signed HTTPS URL.")
        if not target_lang.strip():
            raise ValueError("A target language code is required.")
        response = self._client().dubbing.create(
            source_url=source_url,
            source_lang=source_lang or None,
            target_lang=target_lang,
            name=name,
            num_speakers=max(0, int(num_speakers)),
            watermark=bool(watermark),
            highest_resolution=True,
            disable_voice_cloning=bool(disable_voice_cloning),
        )
        data = _as_dict(response)
        dubbing_id = (
            data.get("dubbing_id")
            or data.get("id")
            or getattr(response, "dubbing_id", None)
            or getattr(response, "id", None)
        )
        if not dubbing_id:
            raise DubbingError("ElevenLabs did not return a dubbing ID.")
        return {
            "dubbing_id": str(dubbing_id),
            "target_lang": target_lang,
            "source_lang": source_lang,
            "raw": data,
        }

    def get(self, dubbing_id: str) -> dict[str, Any]:
        if not dubbing_id.strip():
            raise ValueError("A dubbing ID is required.")
        response = self._client().dubbing.get(dubbing_id)
        data = _as_dict(response)
        data.setdefault("dubbing_id", dubbing_id)
        return data

    def download(self, *, dubbing_id: str, language_code: str, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        stream = self._client().dubbing.audio.get(dubbing_id, language_code)
        with target.open("wb") as handle:
            for chunk in stream:
                handle.write(chunk)
        if not target.exists() or target.stat().st_size == 0:
            raise DubbingError("ElevenLabs returned an empty dubbing file.")
        return target
