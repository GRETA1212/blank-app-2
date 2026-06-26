from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class CharacterProfile:
    name: str
    niche: str
    role: str
    personality: str
    visual_style: str
    voice_style: str
    audience: str
    primary_income: str
    signature_series: tuple[str, ...]
    catchphrase: str


SEED_CHARACTERS: dict[str, CharacterProfile] = {
    "Sofia": CharacterProfile(
        name="Sofia",
        niche="Beauty",
        role="Virtual makeup creator",
        personality="Warm, precise, confident, practical",
        visual_style="Editorial beauty studio, soft daylight, clean close-ups",
        voice_style="Friendly Italian/English creator voice, energetic but not rushed",
        audience="Beauty learners and product shoppers aged 18-34",
        primary_income="Affiliate products, beauty sponsors, salon content packages",
        signature_series=(
            "Makeup Mistake of the Day",
            "One-Minute Transformation",
            "Sofia Tests the Trend",
        ),
        catchphrase="Small change, completely different result.",
    ),
    "Elena": CharacterProfile(
        name="Elena",
        niche="Real Estate",
        role="Virtual property presenter",
        personality="Elegant, curious, trustworthy, commercially aware",
        visual_style="Cinematic property tours, natural light, premium architecture",
        voice_style="Calm presenter voice with clear numbers and confident pacing",
        audience="Property buyers, renters, investors and real-estate professionals",
        primary_income="Property leads, sponsored listings, agent video packages",
        signature_series=(
            "What This Budget Buys",
            "Would You Live Here?",
            "Hidden Feature Home Tour",
        ),
        catchphrase="The detail that changes the whole property is this.",
    ),
    "Luna": CharacterProfile(
        name="Luna",
        niche="Mini Movies",
        role="Lead character in an episodic story universe",
        personality="Intelligent, emotionally brave, mysterious, imperfect",
        visual_style="Cinematic science-fiction drama, moody lighting, recurring locations",
        voice_style="Intimate dramatic narration with deliberate pauses",
        audience="Mystery, romance and short-drama viewers aged 16-34",
        primary_income="Platform views, YouTube compilations, sponsors, memberships",
        signature_series=(
            "Messages From Tomorrow",
            "The Secret Between Us",
            "Viewer Chooses the Ending",
        ),
        catchphrase="Tomorrow already knows what I decide tonight.",
    ),
}


LANGUAGE_COPY: dict[str, dict[str, str]] = {
    "English": {
        "generic_hook": "Most people miss this important detail about {topic}.",
        "setup": "Here is what most people miss about {topic}.",
        "development": "At first it looks simple, but one detail changes the result.",
        "payoff": "The useful part is not the trend itself; it is knowing when and why it works.",
        "cta": "Would you try this? Follow for the next test.",
    },
    "Italian": {
        "generic_hook": "Quasi tutti ignorano questo dettaglio importante su {topic}.",
        "setup": "Ecco cosa quasi tutti ignorano su {topic}.",
        "development": "All'inizio sembra semplice, ma un dettaglio cambia completamente il risultato.",
        "payoff": "La parte utile non è solo la tendenza: è capire quando e perché funziona.",
        "cta": "Lo proveresti? Seguimi per il prossimo test.",
    },
    "Albanian": {
        "generic_hook": "Shumica nuk e vëren këtë detaj të rëndësishëm te {topic}.",
        "setup": "Ja çfarë shumica nuk vëren te {topic}.",
        "development": "Në fillim duket e thjeshtë, por një detaj e ndryshon të gjithë rezultatin.",
        "payoff": "Vlera nuk është vetëm te trendi, por te kuptimi se kur dhe pse funksionon.",
        "cta": "A do ta provoje? Ndiq për testin tjetër.",
    },
    "Macedonian": {
        "generic_hook": "Повеќето луѓе не го забележуваат овој важен детаљ кај {topic}.",
        "setup": "Еве што повеќето луѓе не го забележуваат кај {topic}.",
        "development": "На почеток изгледа едноставно, но еден детаљ го менува целиот резултат.",
        "payoff": "Вредноста не е само во трендот, туку во тоа да знаеш кога и зошто функционира.",
        "cta": "Би го пробал/а ова? Следи за следниот тест.",
    },
}


NICHE_HOOKS: dict[str, dict[str, str]] = {
    "Beauty": {
        "English": "This tiny makeup mistake changes your whole face.",
        "Italian": "Questo piccolo errore di trucco cambia tutto il viso.",
        "Albanian": "Ky gabim i vogël në grim ndryshon gjithë fytyrën.",
        "Macedonian": "Оваа мала грешка во шминкањето го менува целото лице.",
    },
    "Real Estate": {
        "English": "This home looks ordinary until you see what is behind this wall.",
        "Italian": "Questa casa sembra normale finché non vedi cosa c'è dietro questa parete.",
        "Albanian": "Kjo shtëpi duket e zakonshme derisa të shohësh çfarë fshihet pas këtij muri.",
        "Macedonian": "Овој дом изгледа обично сè додека не видиш што има зад овој ѕид.",
    },
    "Mini Movies": {
        "English": "At midnight, Luna received a video recorded tomorrow.",
        "Italian": "A mezzanotte, Luna ha ricevuto un video registrato domani.",
        "Albanian": "Në mesnatë, Luna mori një video të regjistruar nesër.",
        "Macedonian": "На полноќ, Луна доби видео снимено утре.",
    },
}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return value.strip("-") or "video"


def _select_hook(profile: CharacterProfile, topic: str, language: str) -> str:
    niche_hooks = NICHE_HOOKS.get(profile.niche)
    if niche_hooks:
        return niche_hooks.get(language, niche_hooks["English"])
    return LANGUAGE_COPY[language]["generic_hook"].format(topic=topic)


def _hashtags(profile: CharacterProfile, topic: str, platform: str) -> list[str]:
    base = {
        "Beauty": ["beautytips", "makeuptips", "virtualcreator", "beautyvideo"],
        "Real Estate": ["realestate", "hometour", "property", "virtualcreator"],
        "Mini Movies": ["minimovie", "storytime", "mystery", "aistory"],
    }.get(profile.niche, [slugify(profile.niche).replace("-", ""), "virtualcreator", "shortvideo"])
    topic_tag = slugify(topic).replace("-", "")[:24]
    platform_tag = "shorts" if "YouTube" in platform else "tiktok"
    return [f"#{tag}" for tag in [*base, topic_tag, platform_tag] if tag]


def generate_video_plan(
    profile: CharacterProfile,
    topic: str,
    language: str,
    duration_seconds: int,
    objective: str,
    platform: str,
) -> dict[str, Any]:
    language = language if language in LANGUAGE_COPY else "English"
    copy = LANGUAGE_COPY[language]
    hook = _select_hook(profile, topic, language)

    if profile.niche == "Mini Movies":
        setup = copy["setup"].format(topic=topic)
        development = (
            f"{profile.name} watches the clip and notices a detail that could only be known "
            "after tonight's decision. She has one minute to choose whether to trust it."
        )
        payoff = (
            "She follows the warning, but the final frame reveals that the person sending it "
            "is standing behind her."
        )
        cta = f"Should {profile.name} turn around or run? The most-liked choice becomes the next episode."
    else:
        setup = copy["setup"].format(topic=topic)
        development = copy["development"]
        payoff = copy["payoff"]
        cta = copy["cta"]

    script = {
        "hook": hook,
        "setup": setup,
        "development": development,
        "payoff": payoff,
        "call_to_action": cta,
    }

    scene_count = 7 if duration_seconds >= 60 else 5
    scene_duration = round(duration_seconds / scene_count, 1)
    script_lines = [hook, setup, development, payoff, cta]
    scenes: list[dict[str, Any]] = []
    for index in range(scene_count):
        narration = script_lines[min(index, len(script_lines) - 1)]
        scenes.append(
            {
                "scene": index + 1,
                "duration_seconds": scene_duration,
                "narration": narration,
                "visual_prompt": (
                    f"{profile.name}, {profile.visual_style}. Scene {index + 1} about {topic}. "
                    "Vertical 9:16 composition, consistent face and wardrobe, no text in image."
                ),
                "editing_note": "Change framing or action every 2-4 seconds; keep subtitles readable.",
            }
        )

    hashtags = _hashtags(profile, topic, platform)
    caption = f"{hook} {cta} {' '.join(hashtags)}"
    timestamp = datetime.now(timezone.utc)
    project_id = f"{slugify(profile.name)}-{slugify(topic)}-{timestamp.strftime('%Y%m%d%H%M%S')}"

    return {
        "project_id": project_id,
        "created_at": timestamp.isoformat(),
        "character": asdict(profile),
        "topic": topic,
        "language": language,
        "duration_seconds": duration_seconds,
        "objective": objective,
        "platform": platform,
        "script": script,
        "scenes": scenes,
        "caption": caption,
        "hashtags": hashtags,
        "production_checklist": [
            "Confirm the character face and voice remain consistent.",
            "Use only original or properly licensed visuals, audio and music.",
            "Add an AI-generated-content label when the platform requires it.",
            "Check claims about products, prices and properties before publishing.",
            "Export at 1080x1920 with no watermark from another platform.",
        ],
    }


def calculate_growth_score(
    retention_percent: float,
    completion_percent: float,
    shares_per_1000: float,
    followers_per_1000: float,
) -> float:
    retention_component = max(0.0, min(retention_percent, 100.0))
    completion_component = max(0.0, min(completion_percent, 100.0))
    share_component = max(0.0, min(shares_per_1000 / 20.0 * 100.0, 100.0))
    follower_component = max(0.0, min(followers_per_1000 / 20.0 * 100.0, 100.0))
    score = (
        retention_component * 0.35
        + completion_component * 0.25
        + share_component * 0.20
        + follower_component * 0.20
    )
    return round(score, 1)


def calculate_money_projection(
    tiktok_views: int,
    tiktok_qualified_percent: float,
    tiktok_rpm_eur: float,
    youtube_views: int,
    youtube_eligible_percent: float,
    youtube_rpm_eur: float,
    affiliate_income_eur: float = 0.0,
    sponsorship_income_eur: float = 0.0,
    lead_income_eur: float = 0.0,
    production_cost_eur: float = 0.0,
) -> dict[str, float]:
    tiktok_qualified = tiktok_views * max(0.0, min(tiktok_qualified_percent, 100.0)) / 100.0
    youtube_eligible = youtube_views * max(0.0, min(youtube_eligible_percent, 100.0)) / 100.0
    tiktok_revenue = tiktok_qualified / 1000.0 * max(tiktok_rpm_eur, 0.0)
    youtube_revenue = youtube_eligible / 1000.0 * max(youtube_rpm_eur, 0.0)
    gross = tiktok_revenue + youtube_revenue + affiliate_income_eur + sponsorship_income_eur + lead_income_eur
    profit = gross - production_cost_eur
    total_views = tiktok_views + youtube_views
    profit_per_1000 = profit / total_views * 1000.0 if total_views else 0.0
    return {
        "tiktok_qualified_views": round(tiktok_qualified),
        "youtube_eligible_views": round(youtube_eligible),
        "tiktok_revenue_eur": round(tiktok_revenue, 2),
        "youtube_revenue_eur": round(youtube_revenue, 2),
        "gross_income_eur": round(gross, 2),
        "production_cost_eur": round(production_cost_eur, 2),
        "profit_eur": round(profit, 2),
        "profit_per_1000_views_eur": round(profit_per_1000, 4),
    }


def recommend_action(growth_score: float, profit_eur: float, total_views: int) -> str:
    if total_views < 1000:
        return "TEST MORE — there is not enough data yet. Publish at least three variations."
    if growth_score >= 70 and profit_eur > 0:
        return "SCALE — create three follow-up videos using the same hook structure and character."
    if growth_score >= 55:
        return "OPTIMIZE — keep the concept but test a stronger opening and faster payoff."
    if profit_eur > 0:
        return "MONETIZE CAREFULLY — growth is weak, but the audience may still have commercial value."
    return "PAUSE — stop repeating this exact format and test a different topic or character."
