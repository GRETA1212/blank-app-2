from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from character_lab import DEFAULT_CHARACTER_DNA
from studio_bridge import add_video, find_video, load_data, mark_published, save_analytics, save_data, start_production

st.set_page_config(page_title="Studio Control Center", page_icon="🎛️", layout="wide")
data = load_data()

st.title("🎛️ Greta Studio Control Center")
st.caption("Idea → production → rendered MP4 → publish → analytics → decision")

month_key = date.today().strftime("%Y-%m")
month_income = sum(float(x.get("amount_eur", 0)) for x in data["income"] if str(x.get("date", "")).startswith(month_key))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Queued", sum(1 for x in data["videos"] if x["status"] == "QUEUE"))
c2.metric("In production", sum(1 for x in data["videos"] if x["status"] in ["SCRIPTED", "IN_PRODUCTION", "RENDERING", "REVIEW"]))
c3.metric("Ready", sum(1 for x in data["videos"] if x["status"] == "READY"))
c4.metric("Income this month", f"€{month_income:,.2f}")

queue_tab, publish_tab, analytics_tab, income_tab = st.tabs(["Production Queue", "Publish", "Analytics", "Income"])

with queue_tab:
    with st.form("new_video"):
        left, right = st.columns(2)
        with left:
            character = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA.keys()))
            title = st.text_input("Video idea")
            platform = st.selectbox("Platform", ["TikTok", "YouTube Shorts", "TikTok + YouTube Shorts"])
        with right:
            language = st.selectbox("Language", ["Albanian", "Macedonian", "English", "Italian"])
            objective = st.selectbox("Objective", ["Views", "Followers", "Affiliate click", "Sponsor portfolio", "Property lead", "Client inquiry"])
            planned_date = st.date_input("Planned date", value=date.today())
            cost = st.number_input("Expected cost (€)", min_value=0.0, value=0.0, step=1.0)
        submitted = st.form_submit_button("Add to queue", type="primary")
    if submitted:
        if title.strip():
            add_video(data, character, title, platform, planned_date, objective, language, cost)
            st.rerun()
        else:
            st.error("Enter a video idea.")

    if data["videos"]:
        st.dataframe(
            [
                {
                    "Character": x["character"],
                    "Video": x["title"],
                    "Status": x["status"],
                    "Project": x.get("project_id") or "—",
                    "Master MP4": x.get("rendered_path") or "—",
                }
                for x in data["videos"]
            ],
            use_container_width=True,
            hide_index=True,
        )

        selected_id = st.selectbox(
            "Select video",
            [x["id"] for x in data["videos"]],
            format_func=lambda value: f"{find_video(data, value)['character']} — {find_video(data, value)['title']} [{find_video(data, value)['status']}]",
        )
        selected = find_video(data, selected_id)
        if st.button("Start / Open Production", type="primary"):
            project = start_production(data, selected_id)
            st.session_state.reality_project = project
            st.session_state.bridge_video_id = selected_id
            st.switch_page("pages/2_Reality_Pipeline.py")

        if selected.get("rendered_path") and Path(selected["rendered_path"]).exists():
            st.success("Rendered MP4 connected. This video is ready to publish.")
            st.video(selected["rendered_path"])
    else:
        st.info("Add the first Sofia video.")

with publish_tab:
    ready = [x for x in data["videos"] if x["status"] in ["READY", "PUBLISHED"]]
    if not ready:
        st.info("Rendered videos appear here automatically after you reopen this page.")
    else:
        video_id = st.selectbox("Ready video", [x["id"] for x in ready], format_func=lambda value: find_video(data, value)["title"])
        video = find_video(data, video_id)
        if video.get("rendered_path") and Path(video["rendered_path"]).exists():
            st.video(video["rendered_path"])
        with st.form("publish_video"):
            url = st.text_input("Published link", value=video.get("published_url") or "")
            published_date = st.date_input("Published date", value=date.today())
            done = st.form_submit_button("Mark published", type="primary")
        if done:
            mark_published(data, video_id, url, published_date)
            st.rerun()

with analytics_tab:
    published = [x for x in data["videos"] if x["status"] == "PUBLISHED"]
    if not published:
        st.info("Publish a video first.")
    else:
        video_id = st.selectbox("Published video", [x["id"] for x in published], format_func=lambda value: find_video(data, value)["title"], key="analytics_video")
        video = find_video(data, video_id)
        with st.form("analytics"):
            a, b, c = st.columns(3)
            with a:
                views = st.number_input("Views after 72 hours", min_value=0, value=1000, step=100)
                retention = st.number_input("Retention %", 0.0, 100.0, 45.0)
            with b:
                completion = st.number_input("Completion %", 0.0, 100.0, 25.0)
                shares = st.number_input("Shares", min_value=0, value=10)
            with c:
                followers = st.number_input("Followers gained", min_value=0, value=5)
                revenue = st.number_input("Actual income (€)", min_value=0.0, value=0.0)
                cost = st.number_input("Actual cost (€)", min_value=0.0, value=float(video.get("production_cost_eur", 0.0)))
            score = st.form_submit_button("Save and decide", type="primary")
        if score:
            result = save_analytics(data, video_id, views, retention, completion, shares, followers, revenue, cost)
            st.session_state.control_result = result
        result = st.session_state.get("control_result")
        if result:
            r1, r2, r3 = st.columns(3)
            r1.metric("Growth score", result["growth_score"])
            r2.metric("Profit", f"€{result['profit_eur']:,.2f}")
            r3.metric("Decision", result["decision"])

    if data["tests"]:
        st.dataframe(data["tests"], use_container_width=True, hide_index=True)

with income_tab:
    if data["income"]:
        st.dataframe(data["income"], use_container_width=True, hide_index=True)
    else:
        st.info("No separate income records yet.")

    with st.form("income"):
        character = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA.keys()), key="income_character")
        source = st.selectbox("Source", ["TikTok", "YouTube", "Affiliate", "Sponsor", "Property lead", "Client service"])
        amount = st.number_input("Amount (€)", min_value=0.0, value=0.0, step=10.0)
        received = st.date_input("Date", value=date.today(), key="income_date")
        note = st.text_input("Note")
        add = st.form_submit_button("Record income", type="primary")
    if add and amount > 0:
        data["income"].append({"character": character, "source": source, "amount_eur": float(amount), "date": received.isoformat(), "note": note.strip()})
        save_data(data)
        st.rerun()
