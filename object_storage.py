from __future__ import annotations

import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class StorageError(RuntimeError):
    pass


def _safe_key(value: str) -> str:
    parts = []
    for part in Path(value).parts:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", part).strip("-")
        if cleaned:
            parts.append(cleaned)
    return "/".join(parts)


@dataclass(frozen=True)
class StorageSettings:
    bucket: str
    region: str | None
    endpoint_url: str | None
    access_key_id: str | None
    secret_access_key: str | None
    public_base_url: str | None
    prefix: str = "creator-studio"

    @classmethod
    def from_env(cls) -> "StorageSettings":
        return cls(
            bucket=os.getenv("OBJECT_STORAGE_BUCKET", ""),
            region=os.getenv("OBJECT_STORAGE_REGION") or None,
            endpoint_url=os.getenv("OBJECT_STORAGE_ENDPOINT_URL") or None,
            access_key_id=os.getenv("OBJECT_STORAGE_ACCESS_KEY_ID") or None,
            secret_access_key=os.getenv("OBJECT_STORAGE_SECRET_ACCESS_KEY") or None,
            public_base_url=os.getenv("OBJECT_STORAGE_PUBLIC_BASE_URL") or None,
            prefix=os.getenv("OBJECT_STORAGE_PREFIX", "creator-studio").strip("/"),
        )

    @property
    def configured(self) -> bool:
        return bool(self.bucket and self.access_key_id and self.secret_access_key)


class ObjectStorage:
    """S3-compatible storage for provider inputs and publish-ready videos."""

    def __init__(self, settings: StorageSettings | None = None, client: Any | None = None) -> None:
        self.settings = settings or StorageSettings.from_env()
        self._client = client

    @property
    def configured(self) -> bool:
        return self.settings.configured

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.settings.configured:
            raise StorageError("Object storage is not configured.")
        try:
            import boto3
        except ImportError as error:
            raise StorageError("Install boto3 to use S3-compatible object storage.") from error
        self._client = boto3.client(
            "s3",
            region_name=self.settings.region,
            endpoint_url=self.settings.endpoint_url,
            aws_access_key_id=self.settings.access_key_id,
            aws_secret_access_key=self.settings.secret_access_key,
        )
        return self._client

    def object_key(self, project_id: str, local_path: Path, category: str = "assets") -> str:
        suffix = local_path.suffix.lower()
        name = _safe_key(local_path.stem) + suffix
        return "/".join(filter(None, [self.settings.prefix, _safe_key(project_id), _safe_key(category), name]))

    def upload_file(self, local_path: Path, object_key: str) -> str:
        if not local_path.exists() or not local_path.is_file():
            raise StorageError(f"File does not exist: {local_path}")
        key = _safe_key(object_key)
        if not key:
            raise StorageError("Object key cannot be empty.")
        content_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
        self._get_client().upload_file(
            str(local_path),
            self.settings.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    def signed_get_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        key = _safe_key(object_key)
        if self.settings.public_base_url:
            return f"{self.settings.public_base_url.rstrip('/')}/{key}"
        return self._get_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.settings.bucket, "Key": key},
            ExpiresIn=max(60, min(int(expires_seconds), 604800)),
        )

    def upload_and_sign(
        self,
        project_id: str,
        local_path: Path,
        *,
        category: str = "assets",
        expires_seconds: int = 3600,
    ) -> str:
        key = self.object_key(project_id, local_path, category)
        self.upload_file(local_path, key)
        return self.signed_get_url(key, expires_seconds)


def latest_project_asset(project_id: str, folder_name: str) -> Path:
    folder = Path("storage") / "realism_projects" / project_id / folder_name
    candidates = [path for path in folder.glob("*") if path.is_file()] if folder.exists() else []
    if not candidates:
        raise StorageError(f"No project asset found in {folder_name}.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def publish_reference_image(project_id: str, expires_seconds: int = 3600) -> str:
    image = latest_project_asset(project_id, "identity")
    return ObjectStorage().upload_and_sign(
        project_id,
        image,
        category="identity",
        expires_seconds=expires_seconds,
    )


def publish_master_video(project_id: str, expires_seconds: int = 86400) -> str:
    video = Path("storage") / "realism_projects" / project_id / "exports" / f"{project_id}-master.mp4"
    return ObjectStorage().upload_and_sign(
        project_id,
        video,
        category="exports",
        expires_seconds=expires_seconds,
    )
