from __future__ import annotations

import math
import os
from typing import Any, Iterator

from trend_engine import TrendItem, _item, _keyword_fit


class JustOneTikTokSource:
    """Optional structured TikTok search through the official JustOneAPI SDK."""

    def __init__(self, token: str | None = None, client: Any | None = None) -> None:
        self.token = token or os.getenv("JUSTONEAPI_TOKEN", "")
        self._injected_client = client

    @property
    def configured(self) -> bool:
        return bool(self._injected_client is not None or self.token.strip())

    def _client(self):
        if self._injected_client is not None:
            return self._injected_client
        if not self.token:
            raise RuntimeError("JUSTONEAPI_TOKEN is not configured.")
        try:
            from justoneapi import JustOneAPIClient
        except ImportError as error:
            raise RuntimeError("Install justoneapi from requirements.txt.") from error
        return JustOneAPIClient(token=self.token, raise_on_business_error=True)

    def search(
        self,
        keyword: str,
        *,
        niche: str,
        niche_keywords: list[str],
        region: str = "US",
        publish_time: str = "ONE_WEEK",
        sort_type: str = "MOST_LIKED",
        pages: int = 1,
    ) -> list[TrendItem]:
        if not keyword.strip():
            raise ValueError("TikTok search keyword is required.")
        client = self._client()
        results: list[TrendItem] = []
        seen: set[str] = set()
        try:
            for page in range(max(1, min(int(pages), 5))):
                response = client.tiktok.search_post_v1(
                    keyword=keyword.strip(),
                    offset=page * 20,
                    sort_type=sort_type,
                    publish_time=publish_time,
                    region=region,
                )
                if not response.success:
                    raise RuntimeError(response.message or f"JustOneAPI returned code {response.code}.")
                for candidate in _candidate_posts(response.data):
                    title = _first_text(candidate, "desc", "description", "title", "text", "caption")
                    if not title or len(title) < 3:
                        continue
                    post_id = _first_text(candidate, "aweme_id", "awemeId", "post_id", "postId", "id", "video_id")
                    identity = post_id or title.lower()
                    if identity in seen:
                        continue
                    seen.add(identity)
                    stats = _stats(candidate)
                    views = _number(stats, "playCount", "play_count", "views", "viewCount")
                    likes = _number(stats, "diggCount", "digg_count", "likes", "likeCount")
                    comments = _number(stats, "commentCount", "comment_count", "comments")
                    shares = _number(stats, "shareCount", "share_count", "shares")
                    strength = min(100.0, 20.0 + math.log10(max(1.0, views)) * 13.0)
                    engagement = (likes + comments * 2 + shares * 3) / max(views, 1.0) * 100.0
                    author = _author_name(candidate)
                    url = None
                    if post_id and author:
                        url = f"https://www.tiktok.com/@{author}/video/{post_id}"
                    results.append(
                        _item(
                            source="TikTok via JustOneAPI",
                            title=title[:300],
                            url=url,
                            region=region,
                            niche=niche,
                            strength=strength,
                            niche_fit=_keyword_fit(title, niche_keywords),
                            monetization=min(100.0, 45.0 + engagement * 15.0),
                            originality=62.0,
                            production_ease=72.0,
                            metadata={
                                "post_id": post_id,
                                "author": author,
                                "views": int(views),
                                "likes": int(likes),
                                "comments": int(comments),
                                "shares": int(shares),
                                "keyword": keyword,
                                "publish_time": publish_time,
                                "sort_type": sort_type,
                            },
                        )
                    )
        finally:
            close = getattr(client, "close", None)
            if callable(close) and self._injected_client is None:
                close()
        return sorted(results, key=lambda item: item.score, reverse=True)


def _candidate_posts(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _candidate_posts(item)
        return
    if not isinstance(value, dict):
        return
    title = _first_text(value, "desc", "description", "title", "caption")
    identifier = _first_text(value, "aweme_id", "awemeId", "post_id", "postId", "video_id")
    if title and (identifier or any(key in value for key in ("stats", "statistics", "author"))):
        yield value
    for child in value.values():
        if isinstance(child, (dict, list)):
            yield from _candidate_posts(child)


def _first_text(value: dict[str, Any], *keys: str) -> str:
    for key in keys:
        found = value.get(key)
        if isinstance(found, (str, int)) and str(found).strip():
            return str(found).strip()
    for nested_key in ("itemStruct", "aweme_info", "awemeInfo", "item", "video"):
        nested = value.get(nested_key)
        if isinstance(nested, dict):
            found = _first_text(nested, *keys)
            if found:
                return found
    return ""


def _stats(value: dict[str, Any]) -> dict[str, Any]:
    for key in ("stats", "statistics", "statsV2", "statisticsV2"):
        found = value.get(key)
        if isinstance(found, dict):
            return found
    for nested_key in ("itemStruct", "aweme_info", "awemeInfo", "item"):
        nested = value.get(nested_key)
        if isinstance(nested, dict):
            found = _stats(nested)
            if found:
                return found
    return value


def _number(value: dict[str, Any], *keys: str) -> float:
    for key in keys:
        found = value.get(key)
        if isinstance(found, dict):
            found = found.get("value")
        try:
            if found not in (None, ""):
                return float(str(found).replace(",", ""))
        except (TypeError, ValueError):
            continue
    return 0.0


def _author_name(value: dict[str, Any]) -> str:
    author = value.get("author") or value.get("authorInfo")
    if isinstance(author, dict):
        return _first_text(author, "uniqueId", "unique_id", "username", "name")
    for nested_key in ("itemStruct", "aweme_info", "awemeInfo", "item"):
        nested = value.get(nested_key)
        if isinstance(nested, dict):
            found = _author_name(nested)
            if found:
                return found
    return ""
