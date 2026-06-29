from __future__ import annotations

import csv
import io
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse


VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YouTubeIntelligenceError(RuntimeError):
    pass


def extract_video_id(value: str) -> str:
    candidate = (value or "").strip()
    if VIDEO_ID_RE.fullmatch(candidate):
        return candidate
    parsed = urlparse(candidate)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/", "/live/")):
            parts = parsed.path.strip("/").split("/")
            video_id = parts[1] if len(parts) > 1 else ""
        else:
            video_id = ""
    else:
        video_id = ""
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("Enter a valid YouTube video URL or 11-character video ID.")
    return video_id


def fetch_public_transcript(value: str, languages: list[str] | None = None) -> dict[str, Any]:
    """Fetch captions that are publicly available for a video.

    This uses youtube-transcript-api. It does not download the video, bypass
    private captions, or use logged-in browser cookies.
    """
    video_id = extract_video_id(value)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as error:  # pragma: no cover - dependency error
        raise YouTubeIntelligenceError(
            "Install youtube-transcript-api to fetch public captions."
        ) from error

    requested_languages = languages or ["en"]
    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            result = api.fetch(video_id, languages=requested_languages)
            snippets = result.to_raw_data() if hasattr(result, "to_raw_data") else list(result)
        else:  # Compatibility with older library releases.
            snippets = YouTubeTranscriptApi.get_transcript(video_id, languages=requested_languages)
    except Exception as error:
        raise YouTubeIntelligenceError(f"Transcript unavailable: {error}") from error

    rows: list[dict[str, Any]] = []
    for item in snippets:
        if isinstance(item, dict):
            text = str(item.get("text") or "")
            start = float(item.get("start") or 0)
            duration = float(item.get("duration") or 0)
        else:
            text = str(getattr(item, "text", ""))
            start = float(getattr(item, "start", 0))
            duration = float(getattr(item, "duration", 0))
        clean = re.sub(r"\s+", " ", text).strip()
        if clean:
            rows.append({"text": clean, "start": start, "duration": duration})
    return {
        "video_id": video_id,
        "text": " ".join(item["text"] for item in rows),
        "segments": rows,
        "segment_count": len(rows),
    }


@dataclass
class YouTubeDataClient:
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("YOUTUBE_DATA_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _service(self):
        if not self.api_key:
            raise YouTubeIntelligenceError("YOUTUBE_DATA_API_KEY is not configured.")
        try:
            from googleapiclient.discovery import build
        except ImportError as error:  # pragma: no cover
            raise YouTubeIntelligenceError("google-api-python-client is not installed.") from error
        return build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)

    def video_details(self, value: str) -> dict[str, Any]:
        video_id = extract_video_id(value)
        response = (
            self._service()
            .videos()
            .list(part="snippet,statistics,contentDetails,status", id=video_id)
            .execute()
        )
        items = response.get("items") or []
        if not items:
            raise YouTubeIntelligenceError("YouTube did not return this video.")
        item = items[0]
        snippet = item.get("snippet") or {}
        statistics = item.get("statistics") or {}
        return {
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "description": snippet.get("description", ""),
            "tags": snippet.get("tags", []),
            "thumbnail_url": ((snippet.get("thumbnails") or {}).get("high") or {}).get("url", ""),
            "views": int(statistics.get("viewCount") or 0),
            "likes": int(statistics.get("likeCount") or 0),
            "comments": int(statistics.get("commentCount") or 0),
            "duration_iso8601": (item.get("contentDetails") or {}).get("duration", ""),
            "privacy_status": (item.get("status") or {}).get("privacyStatus", ""),
        }

    def comments(self, value: str, max_results: int = 100) -> list[dict[str, Any]]:
        video_id = extract_video_id(value)
        service = self._service()
        remaining = max(1, min(int(max_results), 500))
        token: str | None = None
        rows: list[dict[str, Any]] = []
        while remaining > 0:
            response = (
                service.commentThreads()
                .list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=min(100, remaining),
                    pageToken=token,
                    order="relevance",
                    textFormat="plainText",
                )
                .execute()
            )
            for item in response.get("items") or []:
                top = ((item.get("snippet") or {}).get("topLevelComment") or {})
                snippet = top.get("snippet") or {}
                rows.append(
                    {
                        "comment_id": top.get("id") or item.get("id") or "",
                        "text": snippet.get("textDisplay") or snippet.get("textOriginal") or "",
                        "likes": int(snippet.get("likeCount") or 0),
                        "replies": int((item.get("snippet") or {}).get("totalReplyCount") or 0),
                        "author": snippet.get("authorDisplayName") or "",
                        "published_at": snippet.get("publishedAt") or "",
                    }
                )
            remaining = max_results - len(rows)
            token = response.get("nextPageToken")
            if not token or remaining <= 0:
                break
        return rows[:max_results]


def parse_retention_csv(content: bytes | str) -> list[dict[str, float]]:
    """Parse a YouTube Studio retention export."""
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, float]] = []
    for raw in reader:
        normalized = {str(key).strip().lower(): value for key, value in raw.items() if key is not None}
        ratio_value = _first_value(
            normalized,
            "elapsedvideotimeratio",
            "elapsed video time ratio",
            "video position",
            "position",
            "ratio",
        )
        retention_value = _first_value(
            normalized,
            "audiencewatchratio",
            "audience watch ratio",
            "retention",
            "audience retention",
            "percentage",
        )
        if ratio_value is None or retention_value is None:
            continue
        ratio = _number(ratio_value)
        retention = _number(retention_value)
        if ratio > 1:
            ratio /= 100.0
        if retention <= 1:
            retention *= 100.0
        rows.append(
            {
                "ratio": max(0.0, min(1.0, ratio)),
                "retention": max(0.0, min(100.0, retention)),
            }
        )
    if not rows:
        raise ValueError("No retention rows were recognized in the CSV.")
    return sorted(rows, key=lambda item: item["ratio"])


def _first_value(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _number(value: Any) -> float:
    clean = str(value).strip().replace("%", "").replace(",", ".")
    return float(clean)
