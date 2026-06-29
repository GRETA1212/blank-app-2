from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


NICHE_FILE = Path("storage/niches.json")


DEFAULT_NICHES: dict[str, dict[str, Any]] = {
    "Sofia": {
        "primary_niche": "Beauty",
        "subtopics": ["makeup techniques", "skincare", "product tests", "hair", "beauty mistakes"],
        "keywords": ["makeup", "skincare", "beauty", "eyeliner", "lipstick", "hair"],
        "audience": "Women and beauty learners aged 18-34",
        "competitors": [],
        "products": ["makeup", "skincare", "beauty tools", "digital guides"],
        "avoid_topics": ["medical claims", "unsafe cosmetic procedures", "unverified product claims"],
        "languages": ["English", "Italian", "Albanian", "Macedonian"],
        "platforms": ["TikTok", "YouTube Shorts", "Instagram Reels"],
        "content_pillars": ["education", "transformation", "product demonstration", "trend testing", "personal story"],
    },
    "Elena": {
        "primary_niche": "Real Estate",
        "subtopics": ["home tours", "interior design", "property tips", "renovation", "investment basics"],
        "keywords": ["apartment", "house", "property", "interior", "renovation", "mortgage"],
        "audience": "Property buyers, renters, investors and agents",
        "competitors": [],
        "products": ["property leads", "sponsored listings", "agent video packages"],
        "avoid_topics": ["unverified prices", "legal guarantees", "financial promises"],
        "languages": ["English", "Albanian", "Macedonian"],
        "platforms": ["TikTok", "YouTube Shorts", "Instagram Reels"],
        "content_pillars": ["tour", "comparison", "hidden feature", "buyer education", "design inspiration"],
    },
    "Luna": {
        "primary_niche": "Original Historical Mini-Stories",
        "subtopics": [
            "forgotten women in history",
            "strange true events",
            "lost inventions",
            "ordinary life in past centuries",
            "historical mysteries",
        ],
        "keywords": [
            "forgotten history",
            "history story",
            "true historical event",
            "historical mystery",
            "lost invention",
            "what life was like",
        ],
        "audience": "Curious short-form viewers aged 16-44 who enjoy surprising true stories and cinematic history",
        "competitors": [],
        "products": [
            "YouTube advertising revenue",
            "sponsors",
            "memberships",
            "history story compilations",
            "licensed educational clips",
        ],
        "avoid_topics": [
            "graphic violence",
            "real-person impersonation",
            "copyrighted franchises",
            "invented quotations",
            "unverified historical claims",
            "modern political persuasion",
        ],
        "languages": ["English"],
        "platforms": ["YouTube Shorts", "TikTok", "Instagram Reels"],
        "content_pillars": [
            "surprising hook",
            "documented setting",
            "human conflict",
            "little-known fact",
            "source-backed reveal",
        ],
    },
}


def load_niches() -> dict[str, dict[str, Any]]:
    NICHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not NICHE_FILE.exists():
        data = deepcopy(DEFAULT_NICHES)
        save_niches(data)
        return data
    try:
        data = json.loads(NICHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = deepcopy(DEFAULT_NICHES)
    for character, defaults in DEFAULT_NICHES.items():
        profile = data.setdefault(character, deepcopy(defaults))
        for key, value in defaults.items():
            profile.setdefault(key, deepcopy(value))
    return data


def save_niches(data: dict[str, dict[str, Any]]) -> None:
    NICHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = NICHE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(NICHE_FILE)


def get_niche(character: str) -> dict[str, Any]:
    data = load_niches()
    if character not in data:
        raise KeyError(f"Unknown creator: {character}")
    return deepcopy(data[character])


def update_niche(character: str, profile: dict[str, Any]) -> dict[str, Any]:
    data = load_niches()
    cleaned = {
        "primary_niche": str(profile.get("primary_niche", "")).strip() or "General",
        "subtopics": _clean_list(profile.get("subtopics")),
        "keywords": _clean_list(profile.get("keywords")),
        "audience": str(profile.get("audience", "")).strip(),
        "competitors": _clean_list(profile.get("competitors")),
        "products": _clean_list(profile.get("products")),
        "avoid_topics": _clean_list(profile.get("avoid_topics")),
        "languages": _clean_list(profile.get("languages")),
        "platforms": _clean_list(profile.get("platforms")),
        "content_pillars": _clean_list(profile.get("content_pillars")),
    }
    if not cleaned["keywords"]:
        cleaned["keywords"] = [cleaned["primary_niche"]]
    data[character] = cleaned
    save_niches(data)
    return deepcopy(cleaned)


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, str):
        items = value.replace("\n", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = []
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text.lower() not in {existing.lower() for existing in result}:
            result.append(text)
    return result
