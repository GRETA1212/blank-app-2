from datetime import date

from creator_os import (
    add_trends,
    approve_idea,
    blank_data,
    create_daily_ideas,
    record_income,
    revenue_summary,
)
from niche_manager import get_niche, load_niches, update_niche


def test_niche_profile_persists_and_deduplicates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profile = get_niche("Sofia")
    profile["keywords"] = "makeup, skincare, Makeup"
    saved = update_niche("Sofia", profile)

    assert saved["keywords"] == ["makeup", "skincare"]
    assert load_niches()["Sofia"]["primary_niche"] == "Beauty"


def test_daily_ideas_use_niche_and_skip_avoid_topics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = blank_data()
    add_trends(
        data,
        [
            {
                "id": "safe",
                "source": "YouTube",
                "title": "Simple eyeliner placement test",
                "region": "US",
                "niche": "Beauty",
                "score": 91,
            },
            {
                "id": "blocked",
                "source": "YouTube",
                "title": "Unsafe cosmetic procedures explained",
                "region": "US",
                "niche": "Beauty",
                "score": 99,
            },
        ],
    )
    niche = get_niche("Sofia")
    ideas = create_daily_ideas(
        data,
        character="Sofia",
        language="English",
        platform="TikTok + YouTube Shorts",
        planned_date=date(2026, 6, 29),
        count=2,
        niche_profile=niche,
    )

    assert ideas
    assert all("unsafe cosmetic procedures" not in item["topic"].lower() for item in ideas)
    assert ideas[0]["niche"] == "Beauty"
    assert ideas[0]["audience"] == niche["audience"]


def test_approved_idea_creates_calendar_slot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = blank_data()
    niche = get_niche("Sofia")
    idea = create_daily_ideas(
        data,
        character="Sofia",
        language="English",
        platform="TikTok",
        planned_date=date(2026, 6, 30),
        count=1,
        niche_profile=niche,
    )[0]

    slot = approve_idea(data, idea["id"])

    assert slot["idea_id"] == idea["id"]
    assert slot["date"] == "2026-06-30"
    assert slot["status"] == "PLANNED"


def test_revenue_summary_groups_sources_and_creators(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = blank_data()
    record_income(data, character="Sofia", source="Affiliate", amount_eur=30, occurred_on=date(2026, 6, 29))
    record_income(data, character="Sofia", source="YouTube", amount_eur=20, occurred_on=date(2026, 6, 29))
    record_income(data, character="Elena", source="YouTube", amount_eur=10, occurred_on=date(2026, 6, 29))

    summary = revenue_summary(data)

    assert summary["total_eur"] == 60
    assert summary["by_source"]["YouTube"] == 30
    assert summary["by_character"]["Sofia"] == 50
