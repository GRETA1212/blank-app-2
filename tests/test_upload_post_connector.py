from pathlib import Path

import pytest

from providers import ProviderError
from upload_post_connector import UploadPostConnector


class FakeUploadPostClient:
    def __init__(self):
        self.calls = []

    def create_user(self, username):
        self.calls.append(("create_user", username))
        return {"username": username}

    def generate_jwt(self, username, **kwargs):
        self.calls.append(("generate_jwt", username, kwargs))
        return {"connection_url": "https://example.test/connect"}

    def upload_video(self, path, **kwargs):
        self.calls.append(("upload_video", Path(path), kwargs))
        return {"request_id": "request-1"}

    def get_status(self, request_id):
        return {"request_id": request_id, "status": "completed"}

    def get_job_status(self, job_id):
        return {"job_id": job_id, "status": "scheduled"}

    def get_analytics(self, username, platforms=None):
        return {"username": username, "platforms": platforms}

    def get_post_analytics(self, request_id):
        return {"request_id": request_id, "views": 1000}

    def get_history(self, page=1, limit=20):
        return {"page": page, "limit": limit}

    def get_media(self, platform, username):
        return {"platform": platform, "username": username}

    def list_scheduled(self):
        return {"items": []}

    def cancel_scheduled(self, job_id):
        return {"job_id": job_id, "cancelled": True}


def test_upload_post_sets_platform_safety_flags(tmp_path):
    video = tmp_path / "master.mp4"
    video.write_bytes(b"video")
    fake = FakeUploadPostClient()
    connector = UploadPostConnector(client=fake)

    response = connector.publish_video(
        video,
        username="sofia",
        platforms=["tiktok", "youtube", "instagram"],
        title="Test video",
        description="Test description",
        queue_only=True,
        youtube_privacy="private",
        tiktok_mode="MEDIA_UPLOAD",
        tiktok_privacy="SELF_ONLY",
        is_ai_generated=True,
    )

    assert response["request_id"] == "request-1"
    _, _, options = fake.calls[-1]
    assert options["platforms"] == ["tiktok", "youtube", "instagram"]
    assert options["is_aigc"] is True
    assert options["containsSyntheticMedia"] is True
    assert options["privacyStatus"] == "private"
    assert options["post_mode"] == "MEDIA_UPLOAD"
    assert options["add_to_queue"] is True


def test_connection_link_uses_creator_profile():
    fake = FakeUploadPostClient()
    connector = UploadPostConnector(client=fake)

    result = connector.connection_link("sofia", platforms=["tiktok", "youtube"])

    assert result["connection_url"].startswith("https://")
    _, username, options = fake.calls[-1]
    assert username == "sofia"
    assert options["platforms"] == ["tiktok", "youtube"]
    assert options["show_calendar"] is True


def test_publish_requires_existing_file(tmp_path):
    connector = UploadPostConnector(client=FakeUploadPostClient())
    with pytest.raises(ProviderError, match="Video not found"):
        connector.publish_video(
            tmp_path / "missing.mp4",
            username="sofia",
            platforms=["tiktok"],
            title="Missing",
        )


def test_status_supports_request_or_job_ids():
    connector = UploadPostConnector(client=FakeUploadPostClient())
    assert connector.get_status(request_id="r1")["status"] == "completed"
    assert connector.get_status(job_id="j1")["status"] == "scheduled"
