from __future__ import annotations

from datetime import date

import streamlit as st

from creator_os import approve_idea, create_daily_ideas, link_calendar_video, load_data
from creator_studio import SEED_CHARACTERS
from studio_bridge import add_video, load_data as load_studio_data, save_data as save_studio_data


st.set_page_config(page_title="Daily Planner", page_icon="🗓️", layout="wide")
st.title("🗓️ Daily Content Planner")
st.caption("Turn the strongest trend signals into scripts, shot plans, captions, and production-ready queue items.")

os_data = load_data()
studio_data = load_studio_data()

c1, c2, c3, c4 = st.columns(4)
character = c1.selectbox("Creator", list(SEED_CHARACTERS))
language = c2.selectbox("Language", ["English", "Italian", "Albanian", "Macedonian"])
platform = c3.selectbox("Platform", ["TikTok + YouTube Shorts", "TikTok", "YouTube Shorts"])
planned_date = c4.date_input("Plan for", date.today())
count = st.slider("Ideas to create", 1, 5, 3)

if st.button("Create today's recommendations", type="primary", use_container_width=True):
    created = create_daily_ideas(
        os_data,
        character=character,
        language=language,
        platform=platform,
        planned_date=planned_date,
        count=count,
    )
    st.success(f"Created {len(created)} recommendations.")
    st.rerun()

ideas = [
    item
    for item in os_data["ideas"]
    if item.get("character") == character and item.get("planned_date") == planned_date.isoformat()
]
ideas = sorted(ideas, key=lambda item: float(item.get("trend_score", 0)), reverse=True)

if not ideas:
    st.info("Create recommendations above. Trend Radar data is used when available; otherwise the creator's signature series is used.")
else:
    for idea in ideas:
        plan = idea["plan"]
        with st.expander(
            f"{idea['topic']} — trend score {idea.get('trend_score', 0)} — {idea['status']}",
            expanded=idea == ideas[0],
        ):
            a, b, c = st.columns(3)
            a.metric("Trend source", idea.get("trend_source") or "Signature series")
            b.metric("Trend score", idea.get("trend_score", 0))
            c.metric("Historical fit", idea.get("historical_fit", 50))
            st.markdown(f"**Hook:** {plan['script']['hook']}")
            st.markdown(f"**Payoff:** {plan['script']['payoff']}")
            st.markdown(f"**Call to action:** {plan['script']['call_to_action']}")
            st.text_area(
                "Caption",
                value=plan["caption"],
                key=f"caption_{idea['id']}",
                height=100,
            )
            st.dataframe(
                [
                    {
                        "Shot": scene["scene"],
                        "Seconds": scene["duration_seconds"],
                        "Narration": scene["narration"],
                        "Visual": scene["visual_prompt"],
                    }
                    for scene in plan["scenes"]
                ],
                use_container_width=True,
                hide_index=True,
            )
            if idea["status"] == "PROPOSED":
                if st.button("Approve and send to production queue", key=f"approve_{idea['id']}", type="primary"):
                    approve_idea(os_data, idea["id"])
                    video = add_video(
                        studio_data,
                        character,
                        idea["topic"],
                        platform,
                        planned_date,
                        "Views + monetization",
                        language,
                        0.0,
                    )
                    link_calendar_video(os_data, idea["id"], video["id"])
                    save_studio_data(studio_data)
                    st.success("Idea approved and added to Greta Private Studio.")
                    st.rerun()
            else:
                st.success("Approved and scheduled.")
