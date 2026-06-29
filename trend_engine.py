from __future__ import annotations

import json
import math
import os
import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

from providers.http_client import HttpClient


@dataclass
class TrendItem:
    id: str
    source: str
    title: str
    url: str | None
    discovered_at: str
    region: str
    niche: str
    strength: float
    niche_fit: float
    monetization: float
    originality: float
    production_ease: float
    past_performance_fit: float
    score: float
    metadata: dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def trend_score(
    strength: float,
    niche_fit: float,
    monetization: float,
    originality: float,
    production_ease: float,
    past_performance_fit: float,
) -> float:
    values = [strength, niche_fit, monetization, originality, production_ease, past_performance_fit]
    values = [max(0.0, min(float(value), 100.0)) for value in values]
    score = (
        values[0] * 0.25
        + values[1] * 0.25
        + values[2] * 0.15
        + values[3] * 0.15
        + values[4] * 0.10
        + values[5] * 0.10
    )
    return round(score, 1)


def _item(
    *,
    source: str,
    title: str,
    url: str | None,
    region: str,
    niche: str,
    strength: float,
    niche_fit: float,
    monetization: float = 60.0,
    originality: float = 60.0,
    production_ease: float = 70.0,
    past_performance_fit: float = 50.0,
    metadata: dict[str, Any] | None = None,
) -> TrendItem:
    return TrendItem(
        id=f"trend-{uuid.uuid4().hex[:12]}",
        source=source,
        title=title.strip(),
        url=url,
        discovered_at=_now(),
        region=region,
        niche=niche,
        strength=float(strength),
        niche_fit=float(niche_fit),
        monetization=float(monetization),
        originality=float(originality),
        production_ease=float(production_ease),
        past_performance_fit=float(past_performance_fit),
        score=trend_score(strength, niche_fit, monetization, originality, production_ease, past_performance_fit),
        metadata=dict(metadata or {}),
    )


def _keyword_fit(title: str, niche_keywords: list[str]) -> float:
    lowered = title.lower()
    matches = sum(1 for keyword in niche_keywords if keyword.lower() in lowered)
    if matches == 0:
        return 35.0
    return min(100.0, 55.0 + matches * 15.0)


class YouTubeTrendSource:
    base_url = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str | None = None, http: HttpClient | None = None) -> None:
        self.api_key = api_key or os.getenv("YOUTUBE_DATA_API_KEY", "")
        self.http = http or HttpClient()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def search(
        self,
        query: str,
        *,
        niche: str,
        niche_keywords: list[str],
        region: str = "US",
        days: int = 14,
        max_results: int = 20,
    ) -> list[TrendItem]:
        if not self.api_key:
            raise RuntimeError("YOUTUBE_DATA_API_KEY is not configured.")
        published_after = (datetime.now(timezone.utc) - timedelta(days=max(1, days))).isoformat().replace("+00:00", "Z")
        params = {
            "part": "snippet",
            "type": "video",
            "order": "viewCount",
            "q": query,
            "publishedAfter": published_after,
            "regionCode": region,
            "maxResults": max(1, min(int(max_results), 50)),
            "key": self.api_key,
        }
        search_data = self.http.request_json("GET", f"{self.base_url}/search?{urlencode(params)}")
        ids = [str(item.get("id", {}).get("videoId", "")) for item in search_data.get("items", [])]
        ids = [item for item in ids if item]
        if not ids:
            return []
        video_params = {
            "part": "snippet,statistics",
            "id": ",".join(ids),
            "maxResults": len(ids),
            "key": self.api_key,
        }
        details = self.http.request_json("GET", f"{self.base_url}/videos?{urlencode(video_params)}")
        results: list[TrendItem] = []
        for video in details.get("items", []):
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            title = str(snippet.get("title", "")).strip()
            if not title:
                continue
            views = int(stats.get("viewCount", 0) or 0)
            likes = int(stats.get("likeCount", 0) or 0)
            comments = int(stats.get("commentCount", 0) or 0)
            strength = min(100.0, 15.0 + math.log10(max(1, views)) * 13.5)
            engagement = (likes + comments * 2) / max(views, 1) * 100
            monetization = min(100.0, 45.0 + engagement * 12.0)
            video_id = str(video.get("id", ""))
            results.append(
                _item(
                    source="YouTube",
                    title=title,
                    url=f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                    region=region,
                    niche=niche,
                    strength=strength,
                    niche_fit=_keyword_fit(title, niche_keywords),
                    monetization=monetization,
                    originality=60.0,
                    production_ease=70.0,
                    metadata={
                        "video_id": video_id,
                        "channel_title": snippet.get("channelTitle"),
                        "published_at": snippet.get("publishedAt"),
                        "views": views,
                        "likes": likes,
                        "comments": comments,
                        "query": query,
                    },
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)


class GoogleTrendingNowSource:
    """Reads the RSS export offered by Google Trends Trending Now."""

    def __init__(self, http: HttpClient | None = None) -> None:
        self.http = http or HttpClient()

    def fetch(self, *, niche: str, niche_keywords: list[str], region: str = "US", limit: int = 30) -> list[TrendItem]:
        url = f"https://trends.google.com/trending/rss?geo={region}"
        payload = self.http.request_bytes("GET", url, headers={"User-Agent": "VirtualCreatorStudio/1.0"})
        root = ET.fromstring(payload)
        results: list[TrendItem] = []
        for entry in root.findall(".//item")[: max(1, int(limit))]:
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip() or None
            if not title:
                continue
            traffic_text = ""
            for child in entry:
                if child.tag.endswith("approx_traffic"):
                    traffic_text = (child.text or "").strip()
                    break
            strength = _traffic_strength(traffic_text)
            fit = _keyword_fit(title, niche_keywords)
            results.append(
                _item(
                    source="Google Trends",
                    title=title,
                    url=link,
                    region=region,
                    niche=niche,
                    strength=strength,
                    niche_fit=fit,
                    monetization=55.0,
                    originality=65.0,
                    production_ease=75.0,
                    metadata={"approx_traffic": traffic_text},
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)


def _traffic_strength(value: str) -> float:
    match = re.search(r"([\d,.]+)\s*([KMB]?)", value.upper())
    if not match:
        return 50.0
    number = float(match.group(1).replace(",", ""))
    multiplier = {"": 1.0, "K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0}[match.group(2)]
    traffic = number * multiplier
    return min(100.0, 25.0 + math.log10(max(1.0, traffic)) * 12.5)


def manual_tiktok_trend(
    title: str,
    *,
    niche: str,
    region: str,
    strength: float,
    niche_fit: float,
    monetization: float,
    originality: float,
    production_ease: float,
    url: str | None = None,
    notes: str = "",
) -> TrendItem:
    return _item(
        source="TikTok manual",
        title=title,
        url=url,
        region=region,
        niche=niche,
        strength=strength,
        niche_fit=niche_fit,
        monetization=monetization,
        originality=originality,
        production_ease=production_ease,
        metadata={"notes": notes},
    )


def to_dicts(items: list[TrendItem]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
