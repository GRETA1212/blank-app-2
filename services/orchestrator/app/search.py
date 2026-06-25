import os
from typing import Any
from urllib.parse import urlparse

import httpx

SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "http://localhost:8080")


async def web_search(query: str, language: str = "en", limit: int = 8) -> list[dict[str, Any]]:
    params = {
        "q": query,
        "format": "json",
        "language": language,
        "safesearch": 1,
        "categories": "general",
    }
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(f"{SEARXNG_BASE_URL}/search", params=params)
        response.raise_for_status()
    data = response.json()
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in data.get("results", []):
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        if not url or not title or url in seen:
            continue
        seen.add(url)
        publisher = urlparse(url).netloc.removeprefix("www.")
        output.append(
            {
                "title": title,
                "url": url,
                "publisher": publisher,
                "published_date": str(item.get("publishedDate") or item.get("published_date") or ""),
                "snippet": str(item.get("content") or "")[:1000],
            }
        )
        if len(output) >= limit:
            break
    return output
