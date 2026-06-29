from __future__ import annotations

import os
from pathlib import Path

from .base import ProviderError, VoiceRequest
from .http_client import HttpClient


class ElevenLabsVoiceProvider:
    """Generate speech only with a licensed synthetic voice or documented consent."""

    name = "elevenlabs"
    base_url = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str | None = None, voice_id: str | None = None, model_id: str | None = None, http: HttpClient | None = None) -> None:
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "")
        self.model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        self.http = http or HttpClient()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.voice_id)

    def synthesize(self, request: VoiceRequest, output_path: Path) -> Path:
        if not self.api_key:
            raise ProviderError("ELEVENLABS_API_KEY is not configured.")
        selected_voice = request.voice_id or self.voice_id
        if not selected_voice:
            raise ProviderError("A licensed or consented ElevenLabs voice ID is required.")
        if not request.text.strip():
            raise ProviderError("Voice text cannot be empty.")

        audio = self.http.request_bytes(
            "POST",
            f"{self.base_url}/text-to-speech/{selected_voice}?output_format={request.output_format}",
            headers={"xi-api-key": self.api_key, "Accept": "audio/mpeg"},
            payload={
                "text": request.text.strip(),
                "model_id": request.model_id or self.model_id,
                "voice_settings": {
                    "stability": request.stability,
                    "similarity_boost": request.similarity_boost,
                    "style": request.style,
                    "speed": request.speed,
                    "use_speaker_boost": True,
                },
            },
        )
        if not audio:
            raise ProviderError("ElevenLabs returned an empty audio file.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio)
        return output_path
