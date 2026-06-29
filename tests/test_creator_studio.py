from creator_studio import (
    SEED_CHARACTERS,
    calculate_growth_score,
    calculate_money_projection,
    generate_video_plan,
    recommend_action,
)


def test_generate_video_plan_for_sofia() -> None:
    plan = generate_video_plan(
        profile=SEED_CHARACTERS["Sofia"],
        topic="summer soft glam",
        language="English",
        duration_seconds=70,
        objective="Affiliate product clicks",
        platform="TikTok + YouTube Shorts",
    )

    assert plan["character"]["name"] == "Sofia"
    assert plan["duration_seconds"] == 70
    assert len(plan["scenes"]) == 7
    assert plan["script"]["hook"]
    assert "#beautytips" in plan["hashtags"]


def test_growth_score_stays_between_zero_and_100() -> None:
    score = calculate_growth_score(
        retention_percent=75,
        completion_percent=60,
        shares_per_1000=18,
        followers_per_1000=14,
    )
    assert 0 <= score <= 100
    assert score > 60


def test_money_projection_uses_qualified_views() -> None:
    result = calculate_money_projection(
        tiktok_views=1_000_000,
        tiktok_qualified_percent=50,
        tiktok_rpm_eur=0.40,
        youtube_views=1_000_000,
        youtube_eligible_percent=80,
        youtube_rpm_eur=0.05,
        production_cost_eur=100,
    )

    assert result["tiktok_qualified_views"] == 500_000
    assert result["youtube_eligible_views"] == 800_000
    assert result["tiktok_revenue_eur"] == 200.0
    assert result["youtube_revenue_eur"] == 40.0
    assert result["profit_eur"] == 140.0


def test_recommendation_scales_strong_profitable_video() -> None:
    decision = recommend_action(growth_score=82, profit_eur=120, total_views=50_000)
    assert decision.startswith("SCALE")
