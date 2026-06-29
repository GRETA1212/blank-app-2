from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from providers import ProviderError


SUPPORTED_VIDEO_PLATFORMS = [
    "tiktok",
    "instagram",
    "youtube",
    "linkedin",
    "facebook",
    "pinterest",
    "threads",
    "bluesky",
    "x",
    "discord",
    "telegram",
]


class UploadPostConnector:
    """Single publishing adapter for connected social profiles.

    The Upload-Post API key stays server-side. Each creator maps to an
    Upload-Post profile username that owns its connected social accounts.
    """

    def __init__(self, api_key: str | None = None, client: Any | None = None) -> None:
        self.api_key = api_key or os.getenv("UPLOAD_POST_API_KEY", "")
        self._injected_client = client

    @property
    def configured(self) -> bool:
        return bool(self._injected_client is not None or self.api_key.strip())

    def _client(self):
        if self._injected_client is not None:
            return self._injected_client
        if not self.configured:
            raise ProviderError("UPLOAD_POST_API_KEY is not configured.")
        try:
            from upload_post import UploadPostClient
        except ImportError as error:
            raise ProviderError("Install upload-post from requirements.txt.") from error
        return UploadPostClient(self.api_key)

    def list_profiles(self) -> dict[str, Any]:
        return self._client().list_users()

    def create_profile(self, username: str) -> dict[str, Any]:
        username = username.strip()
        if not username:
            raise ProviderError("Profile username is required.")
        return self._client().create_user(username)

    def connection_link(
        self,
        username: str,
        *,
        redirect_url: str | None = None,
        platforms: list[str] | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        return self._client().generate_jwt(
            username,
            redirect_url=redirect_url,
            platforms=platforms or ["tiktok", "instagram", "youtube"],
            show_calendar=True,
            connect_title="Connect your creator accounts",
            connect_description="Authorize the platforms used by Virtual Creator Money Studio.",
            language=language,
        )

    def publish_video(
        self,
        video_path: Path,
        *,
        username: str,
        platforms: list[str],
        title: str,
        description: str = "",
        scheduled_date: str | None = None,
        timezone: str = "Europe/Skopje",
        queue_only: bool = False,
        first_comment: str | None = None,
        youtube_tags: list[str] | None = None,
        youtube_privacy: str = "private",
        tiktok_mode: str = "MEDIA_UPLOAD",
        tiktok_privacy: str = "SELF_ONLY",
        is_ai_generated: bool = True,
        has_paid_product_placement: bool = False,
        autogenerate_copy: bool = False,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        if not video_path.exists() or not video_path.is_file():
            raise ProviderError(f"Video not found: {video_path}")
        selected = [item.lower() for item in platforms if item.lower() in SUPPORTED_VIDEO_PLATFORMS]
        if not selected:
            raise ProviderError("Select at least one supported platform.")
        if not username.strip():
            raise ProviderError("Upload-Post profile username is required.")
        try:
            return self._client().upload_video(
                video_path,
                title=title.strip() or video_path.stem,
                user=username.strip(),
                platforms=selected,
                description=description.strip() or None,
                first_comment=first_comment.strip() if first_comment else None,
                scheduled_date=scheduled_date,
                timezone=timezone,
                add_to_queue=bool(queue_only),
                async_upload=True,
                autogenerate=bool(autogenerate_copy),
                autogenerate_language=language_code,
                privacy_level=tiktok_privacy,
                post_mode=tiktok_mode,
                is_aigc=bool(is_ai_generated),
                disable_duet=False,
                disable_comment=False,
                disable_stitch=False,
                privacyStatus=youtube_privacy,
                tags=list(youtube_tags or []),
                selfDeclaredMadeForKids=False,
                containsSyntheticMedia=bool(is_ai_generated),
                hasPaidProductPlacement=bool(has_paid_product_placement),
                media_type="REELS",
                share_to_feed=True,
            )
        except Exception as error:
            raise ProviderError(f"Upload-Post publishing failed: {error}") from error

    def get_status(self, request_id: str | None = None, job_id: str | None = None) -> dict[str, Any]:
        if request_id:
            return self._client().get_status(request_id)
        if job_id:
            return self._client().get_job_status(job_id)
        raise ProviderError("A request ID or job ID is required.")

    def get_history(self, page: int = 1, limit: int = 20) -> dict[str, Any]:
        return self._client().get_history(page=page, limit=limit)

    def get_profile_analytics(self, username: str, platforms: list[str] | None = None) -> dict[str, Any]:
        return self._client().get_analytics(username, platforms=platforms)

    def get_post_analytics(self, request_id: str) -> dict[str, Any]:
        return self._client().get_post_analytics(request_id)

    def get_media(self, platform: str, username: str) -> dict[str, Any]:
        return self._client().get_media(platform, username)

    def list_scheduled(self) -> dict[str, Any]:
        return self._client().list_scheduled()

    def cancel_scheduled(self, job_id: str) -> dict[str, Any]:
        return self._client().cancel_scheduled(job_id)
