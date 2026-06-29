from pathlib import Path

import pytest

from character_lab import clone_default_character
from generation_orchestrator import build_generation_plan
from providers import (
    ElevenLabsVoiceProvider,
    HeyGenVideoProvider,
    JobStatus,
    ProviderError,
    RunwayVideoProvider,
    VideoRequest,
    VoiceRequest,
)
from realism_pipeline import RealismProject, RightsRecord, default_shot_plan, save_project, utc_now_iso


class FakeHttp:
    def __init__(self, json_responses=None, byte_response=b"audio"):
        self.json_responses = list(json_responses or [])
        self.byte_response = byte_response
        self.calls = []

    def request_json(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.json_responses.pop(0)

    def request_bytes(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.byte_response


def rights(approved=True):
    return RightsRecord(
        actor_consent=approved,
        face_identity_is_fictional_or_authorized=approved,
        voice_is_licensed_or_consented=approved,
        property_and_product_media_authorized=approved,
        ai_disclosure_required=True,
    )


def project(approved=True):
    character = clone_default_character("Sofia")
    return RealismProject(
        project_id="sofia-provider-test",
        character_name="Sofia",
        topic="eyeliner placement",
        workflow_mode="Actor performance + fictional identity transfer",
        target_language="Italian",
        platform="TikTok + YouTube Shorts",
        created_at=utc_now_iso(),
        rights=rights(approved),
        shots=default_shot_plan(character, "eyeliner placement"),
    )


def test_generation_plan_routes_talking_and_broll_shots(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    current = project()
    save_project(current)

    plan = build_generation_plan(current)

    assert [item["provider"] for item in plan["shots"]] == ["heygen", "runway", "heygen", "runway", "heygen"]
    assert Path("storage/realism_projects/sofia-provider-test/manifests/provider_generation_plan.json").exists()


def test_generation_plan_is_blocked_without_rights(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ProviderError, match="rights gate"):
        build_generation_plan(project(approved=False))


def test_runway_adapter_submits_and_reads_task():
    http = FakeHttp([
        {"id": "runway-task"},
        {"id": "runway-task", "status": "SUCCEEDED", "output": ["https://example.test/shot.mp4"]},
    ])
    provider = RunwayVideoProvider(api_key="test", http=http)
    request = VideoRequest(
        project_id="p1",
        shot_number=2,
        prompt="Natural phone-recorded lifestyle shot",
        duration_seconds=5,
        reference_image_url="https://example.test/sofia.jpg",
    )

    created = provider.create_video(request)
    completed = provider.get_job(created.job_id)

    assert created.status is JobStatus.QUEUED
    assert completed.status is JobStatus.SUCCEEDED
    assert completed.output_url == "https://example.test/shot.mp4"
    assert http.calls[0][2]["payload"]["ratio"] == "720:1280"


def test_heygen_adapter_uses_authorized_avatar_and_script():
    http = FakeHttp([
        {"data": {"video_id": "heygen-video", "status": "queued"}},
        {"data": {"id": "heygen-video", "status": "completed", "video_url": "https://example.test/talking.mp4"}},
    ])
    provider = HeyGenVideoProvider(api_key="test", default_avatar_id="avatar-1", http=http)
    request = VideoRequest(
        project_id="p1",
        shot_number=1,
        prompt="Talking creator",
        script="This is a test.",
        duration_seconds=5,
    )

    created = provider.create_video(request)
    completed = provider.get_job(created.job_id)

    assert created.job_id == "heygen-video"
    assert completed.status is JobStatus.SUCCEEDED
    assert http.calls[0][2]["payload"]["avatar_id"] == "avatar-1"
    assert http.calls[0][2]["payload"]["aspect_ratio"] == "9:16"


def test_elevenlabs_adapter_writes_audio(tmp_path):
    http = FakeHttp(byte_response=b"mp3-data")
    provider = ElevenLabsVoiceProvider(api_key="test", voice_id="voice-1", http=http)
    output = provider.synthesize(VoiceRequest(text="Authorized voice test"), tmp_path / "voice.mp3")

    assert output.read_bytes() == b"mp3-data"
    assert http.calls[0][2]["headers"]["xi-api-key"] == "test"
