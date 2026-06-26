from __future__ import annotations

import json
from dataclasses import asdict

import streamlit as st

from creator_studio import (
    CharacterProfile,
    SEED_CHARACTERS,
    calculate_growth_score,
    calculate_money_projection,
    generate_video_plan,
    recommend_action,
)


st.set_page_config(
    page_title="Virtual Creator Money Studio",
    page_icon="🎬",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
      .hero {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 18px;
        padding: 24px;
        background: linear-gradient(135deg, rgba(111,66,193,.22), rgba(14,165,233,.12));
        margin-bottom: 18px;
      }
      .hero h1 {margin: 0 0 6px 0; font-size: 2rem;}
      .muted {opacity: .74;}
      .character-card {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 16px;
        padding: 18px;
        min-height: 300px;
      }
      .money-box {
        border-left: 4px solid #22c55e;
        padding: 12px 16px;
        background: rgba(34,197,94,.08);
        border-radius: 8px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


if "characters" not in st.session_state:
    st.session_state.characters = dict(SEED_CHARACTERS)
if "drafts" not in st.session_state:
    st.session_state.drafts = []
if "tests" not in st.session_state:
    st.session_state.tests = []


st.markdown(
    """
    <div class="hero">
      <h1>🎬 Virtual Creator Money Studio</h1>
      <div class="muted">Build, test and scale virtual creators based on audience growth and real profit.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Studio",
    [
        "Dashboard",
        "Characters",
        "Create Video",
        "Viral Test Lab",
        "Money Simulator",
        "30-Day Launch Plan",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Phase 1: plan → publish manually → record results → scale winners")


def render_character_card(profile: CharacterProfile) -> None:
    series = "<br>• ".join(profile.signature_series)
    st.markdown(
        f"""
        <div class="character-card">
          <h3>{profile.name}</h3>
          <b>{profile.role}</b><br><br>
          <b>Niche:</b> {profile.niche}<br>
          <b>Audience:</b> {profile.audience}<br><br>
          <b>Personality:</b> {profile.personality}<br><br>
          <b>Income:</b> {profile.primary_income}<br><br>
          <b>Series:</b><br>• {series}<br><br>
          <i>“{profile.catchphrase}”</i>
        </div>
        """,
        unsafe_allow_html=True,
    )


if page == "Dashboard":
    st.subheader("Control room")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active characters", len(st.session_state.characters))
    c2.metric("Video drafts", len(st.session_state.drafts))
    c3.metric("Published tests recorded", len(st.session_state.tests))
    total_views = sum(int(item.get("views", 0)) for item in st.session_state.tests)
    c4.metric("Tracked views", f"{total_views:,}")

    st.markdown("### Starting portfolio")
    cols = st.columns(3)
    for column, profile in zip(cols, list(st.session_state.characters.values())[:3]):
        with column:
            render_character_card(profile)

    st.markdown("### The studio loop")
    st.code(
        "Research pattern → choose character → generate plan → produce video → human review → "
        "publish → record retention and revenue → scale or pause",
        language=None,
    )

    if st.session_state.tests:
        st.markdown("### Latest test decisions")
        rows = [
            {
                "Character": item["character"],
                "Topic": item["topic"],
                "Views": item["views"],
                "Growth score": item["growth_score"],
                "Profit (€)": item["profit_eur"],
                "Decision": item["decision"],
            }
            for item in reversed(st.session_state.tests[-10:])
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

elif page == "Characters":
    st.subheader("Character bibles")
    st.caption("Every virtual creator needs one clear niche, a consistent identity and a specific money route.")

    columns = st.columns(3)
    for index, profile in enumerate(st.session_state.characters.values()):
        with columns[index % 3]:
            render_character_card(profile)

    st.divider()
    with st.expander("Add another character"):
        with st.form("new_character"):
            name = st.text_input("Character name")
            niche = st.text_input("Niche", placeholder="Travel, fitness, food, finance...")
            role = st.text_input("Role", placeholder="Virtual travel guide")
            personality = st.text_area("Personality")
            visual_style = st.text_area("Visual style")
            voice_style = st.text_area("Voice style")
            audience = st.text_input("Target audience")
            income = st.text_input("Primary income route")
            series = st.text_area("Three recurring series, one per line")
            catchphrase = st.text_input("Catchphrase")
            submitted = st.form_submit_button("Create character")

        if submitted:
            clean_name = name.strip()
            if not clean_name or not niche.strip():
                st.error("Name and niche are required.")
            elif clean_name in st.session_state.characters:
                st.error("A character with this name already exists.")
            else:
                profile = CharacterProfile(
                    name=clean_name,
                    niche=niche.strip(),
                    role=role.strip() or f"Virtual {niche.strip()} creator",
                    personality=personality.strip() or "Clear, recognizable and audience-focused",
                    visual_style=visual_style.strip() or "Consistent cinematic vertical-video style",
                    voice_style=voice_style.strip() or "Natural creator voice",
                    audience=audience.strip() or "Defined niche audience",
                    primary_income=income.strip() or "Views, affiliate links and sponsorships",
                    signature_series=tuple(
                        line.strip() for line in series.splitlines() if line.strip()
                    )[:3]
                    or ("Daily Test", "Viewer Question", "Weekly Story"),
                    catchphrase=catchphrase.strip() or "Let us test what really works.",
                )
                st.session_state.characters[clean_name] = profile
                st.success(f"{clean_name} was added to the studio.")
                st.rerun()

elif page == "Create Video":
    st.subheader("Generate a production-ready video plan")
    st.caption("This first version creates the character brief, hook, script, scenes, caption and checklist. Rendering comes next.")

    with st.form("create_video"):
        left, right = st.columns(2)
        with left:
            character_name = st.selectbox("Character", list(st.session_state.characters.keys()))
            topic = st.text_input("Video topic", placeholder="Soft glam mistake, hidden apartment room, message from tomorrow...")
            language = st.selectbox("Language", ["English", "Italian", "Albanian", "Macedonian"])
        with right:
            platform = st.selectbox("Platform", ["TikTok + YouTube Shorts", "TikTok", "YouTube Shorts"])
            duration = st.slider("Target duration", min_value=20, max_value=90, value=70, step=5)
            objective = st.selectbox(
                "Money objective",
                [
                    "Platform views",
                    "Affiliate product clicks",
                    "Property leads",
                    "Sponsor portfolio",
                    "Follower growth",
                ],
            )
        generate = st.form_submit_button("Generate video plan", type="primary")

    if generate:
        if not topic.strip():
            st.error("Enter a topic first.")
        else:
            profile = st.session_state.characters[character_name]
            plan = generate_video_plan(
                profile=profile,
                topic=topic.strip(),
                language=language,
                duration_seconds=duration,
                objective=objective,
                platform=platform,
            )
            st.session_state.drafts.append(plan)
            st.session_state.latest_plan = plan
            st.success("Video plan created and saved in the draft queue.")

    plan = st.session_state.get("latest_plan")
    if plan:
        st.markdown(f"### {plan['character']['name']} — {plan['topic']}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Duration", f"{plan['duration_seconds']} sec")
        m2.metric("Scenes", len(plan["scenes"]))
        m3.metric("Objective", plan["objective"])

        st.markdown("#### Script")
        for label, text in plan["script"].items():
            st.text_area(label.replace("_", " ").title(), value=text, height=90, key=f"{plan['project_id']}-{label}")

        st.markdown("#### Scene list")
        st.dataframe(plan["scenes"], use_container_width=True, hide_index=True)

        st.markdown("#### Caption")
        st.code(plan["caption"], language=None)

        st.markdown("#### Human quality check")
        for item in plan["production_checklist"]:
            st.checkbox(item, key=f"{plan['project_id']}-{item}")

        st.download_button(
            "Download production package (JSON)",
            data=json.dumps(plan, indent=2, ensure_ascii=False),
            file_name=f"{plan['project_id']}.json",
            mime="application/json",
        )

    if st.session_state.drafts:
        st.divider()
        st.markdown("### Draft queue")
        draft_rows = [
            {
                "ID": item["project_id"],
                "Character": item["character"]["name"],
                "Topic": item["topic"],
                "Platform": item["platform"],
                "Duration": item["duration_seconds"],
                "Objective": item["objective"],
            }
            for item in reversed(st.session_state.drafts)
        ]
        st.dataframe(draft_rows, use_container_width=True, hide_index=True)

elif page == "Viral Test Lab":
    st.subheader("Record a published video and let the studio decide")
    st.caption("Do not judge only by views. Retention, completion, shares, follower conversion and profit determine the winner.")

    with st.form("viral_test"):
        a, b, c = st.columns(3)
        with a:
            character = st.selectbox("Character", list(st.session_state.characters.keys()), key="test_character")
            test_topic = st.text_input("Topic / episode")
            views = st.number_input("Views after 72 hours", min_value=0, value=1000, step=100)
        with b:
            retention = st.number_input("Average retention %", min_value=0.0, max_value=100.0, value=45.0)
            completion = st.number_input("Completion rate %", min_value=0.0, max_value=100.0, value=25.0)
            shares = st.number_input("Total shares", min_value=0, value=10)
        with c:
            followers = st.number_input("Followers gained", min_value=0, value=5)
            revenue = st.number_input("Actual income €", min_value=0.0, value=0.0, step=1.0)
            cost = st.number_input("Production cost €", min_value=0.0, value=0.0, step=1.0)
        save_test = st.form_submit_button("Score and save test", type="primary")

    if save_test:
        shares_per_1000 = shares / views * 1000 if views else 0.0
        followers_per_1000 = followers / views * 1000 if views else 0.0
        growth = calculate_growth_score(retention, completion, shares_per_1000, followers_per_1000)
        profit = round(revenue - cost, 2)
        decision = recommend_action(growth, profit, int(views))
        record = {
            "character": character,
            "topic": test_topic.strip() or "Untitled test",
            "views": int(views),
            "retention_percent": retention,
            "completion_percent": completion,
            "shares": int(shares),
            "followers_gained": int(followers),
            "growth_score": growth,
            "revenue_eur": revenue,
            "cost_eur": cost,
            "profit_eur": profit,
            "decision": decision,
        }
        st.session_state.tests.append(record)
        st.session_state.latest_test = record

    latest = st.session_state.get("latest_test")
    if latest:
        x1, x2, x3 = st.columns(3)
        x1.metric("Growth score", f"{latest['growth_score']}/100")
        x2.metric("Profit", f"€{latest['profit_eur']:,.2f}")
        x3.metric("Views", f"{latest['views']:,}")
        st.info(latest["decision"])

    if st.session_state.tests:
        st.markdown("### Experiment history")
        st.dataframe(st.session_state.tests, use_container_width=True, hide_index=True)
        st.download_button(
            "Download test data (JSON)",
            data=json.dumps(st.session_state.tests, indent=2, ensure_ascii=False),
            file_name="virtual-creator-tests.json",
            mime="application/json",
        )

elif page == "Money Simulator":
    st.subheader("Revenue and profit simulator")
    st.warning("RPM values are assumptions, not guarantees. Replace them with the actual numbers shown in your monetization dashboards.")

    left, right = st.columns(2)
    with left:
        st.markdown("#### TikTok")
        tiktok_views = st.number_input("TikTok views", min_value=0, value=1_000_000, step=100_000)
        tiktok_qualified = st.slider("Qualified-view percentage", 0, 100, 60)
        tiktok_rpm = st.number_input("TikTok RPM € per 1,000 qualified views", min_value=0.0, value=0.30, step=0.05)

        st.markdown("#### Other income")
        affiliate = st.number_input("Affiliate income €", min_value=0.0, value=0.0, step=10.0)
        lead_income = st.number_input("Lead / client income €", min_value=0.0, value=0.0, step=50.0)

    with right:
        st.markdown("#### YouTube Shorts")
        youtube_views = st.number_input("YouTube Shorts views", min_value=0, value=1_000_000, step=100_000)
        youtube_eligible = st.slider("Eligible-view percentage", 0, 100, 80)
        youtube_rpm = st.number_input("YouTube Shorts RPM € per 1,000 eligible views", min_value=0.0, value=0.05, step=0.01)

        st.markdown("#### Commercial income and costs")
        sponsorship = st.number_input("Sponsorship income €", min_value=0.0, value=0.0, step=50.0)
        production_cost = st.number_input("Total production cost €", min_value=0.0, value=100.0, step=10.0)

    projection = calculate_money_projection(
        tiktok_views=int(tiktok_views),
        tiktok_qualified_percent=float(tiktok_qualified),
        tiktok_rpm_eur=float(tiktok_rpm),
        youtube_views=int(youtube_views),
        youtube_eligible_percent=float(youtube_eligible),
        youtube_rpm_eur=float(youtube_rpm),
        affiliate_income_eur=float(affiliate),
        sponsorship_income_eur=float(sponsorship),
        lead_income_eur=float(lead_income),
        production_cost_eur=float(production_cost),
    )

    st.markdown("### Projection")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("TikTok revenue", f"€{projection['tiktok_revenue_eur']:,.2f}")
    r2.metric("YouTube revenue", f"€{projection['youtube_revenue_eur']:,.2f}")
    r3.metric("Gross income", f"€{projection['gross_income_eur']:,.2f}")
    r4.metric("Estimated profit", f"€{projection['profit_eur']:,.2f}")

    st.markdown(
        f"""
        <div class="money-box">
          Qualified TikTok views: <b>{projection['tiktok_qualified_views']:,.0f}</b><br>
          Eligible YouTube views: <b>{projection['youtube_eligible_views']:,.0f}</b><br>
          Profit per 1,000 total views: <b>€{projection['profit_per_1000_views_eur']:.4f}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

elif page == "30-Day Launch Plan":
    st.subheader("First 30 days: prove the model before expanding to 20 characters")

    phases = [
        {
            "Days": "1-3",
            "Mission": "Lock the character bibles",
            "Output": "Sofia, Elena and Luna: face reference, voice, wardrobe, locations and three repeatable series each",
        },
        {
            "Days": "4-10",
            "Mission": "Create nine pilots",
            "Output": "Three original videos per character, each with a different hook structure",
        },
        {
            "Days": "11-20",
            "Mission": "Publish and measure",
            "Output": "Manual posting; record 1-hour, 24-hour and 72-hour retention, completion, shares and followers",
        },
        {
            "Days": "21-27",
            "Mission": "Repeat winners",
            "Output": "Create follow-ups only for the strongest topic/character combinations",
        },
        {
            "Days": "28-30",
            "Mission": "Money review",
            "Output": "Choose the view winner, profit winner and character to pause; define month-two production allocation",
        },
    ]
    st.dataframe(phases, use_container_width=True, hide_index=True)

    st.markdown("### Production allocation after the first test")
    st.progress(70, text="70% — proven winning characters and formats")
    st.progress(20, text="20% — promising formats that need improvement")
    st.progress(10, text="10% — new experiments")

    st.markdown("### Definition of success")
    st.markdown(
        """
        - At least 30 original videos published across the first three characters.
        - One repeatable format that beats the others on retention and follower conversion.
        - A documented cost per video and profit per 1,000 views.
        - A clear decision to scale, optimize or pause each character.
        - No expansion to character four until the workflow is reliable.
        """
    )

    st.markdown("### Next engineering milestone")
    st.info(
        "Add media uploads, consistent character reference images, voice generation, subtitles and FFmpeg rendering. "
        "Publishing remains manual until quality and account safety are proven."
    )
