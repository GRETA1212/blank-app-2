from datetime import date
from pathlib import Path

import streamlit as st

from character_lab import DEFAULT_CHARACTER_DNA
from realism_pipeline import save_project
from studio_bridge import add_video, find_video, load_data, mark_published, save_analytics, save_data, start_production

st.set_page_config(page_title="Greta Private Studio", page_icon="👑", layout="wide")
data = load_data()

st.title("👑 Greta Private Studio")
st.caption("One connected workflow: idea → production → MP4 → publish → analytics")

q, p, a, money = st.tabs(["Queue", "Publish", "Analytics", "Income"])

with q:
    with st.form("add_video"):
        c1, c2 = st.columns(2)
        with c1:
            character = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA))
            title = st.text_input("Video idea")
            platform = st.selectbox("Platform", ["TikTok", "YouTube Shorts", "TikTok + YouTube Shorts"])
        with c2:
            language = st.selectbox("Language", ["Albanian", "Macedonian", "English", "Italian"])
            objective = st.selectbox("Objective", ["Views", "Followers", "Affiliate click", "Sponsor portfolio", "Property lead", "Client inquiry"])
            planned = st.date_input("Planned date", date.today())
            cost = st.number_input("Expected cost (€)", min_value=0.0, value=0.0)
        add = st.form_submit_button("Add to queue", type="primary")
    if add:
        if title.strip():
            add_video(data, character, title, platform, planned, objective, language, cost)
            st.rerun()
        else:
            st.error("Enter a video idea.")

    if data["videos"]:
        st.dataframe(
            [{"Character": v["character"], "Video": v["title"], "Status": v["status"], "Project": v.get("project_id") or "—", "MP4": v.get("rendered_path") or "—"} for v in data["videos"]],
            use_container_width=True,
            hide_index=True,
        )
        video_id = st.selectbox("Select video", [v["id"] for v in data["videos"]], format_func=lambda x: f"{find_video(data, x)['character']} — {find_video(data, x)['title']} [{find_video(data, x)['status']}]")
        video = find_video(data, video_id)

        if not video.get("project_id"):
            st.markdown("#### Confirm rights before creating the production project")
            actor = st.checkbox("Performance is mine or from a consenting actor")
            face = st.checkbox("Character face is fictional or authorized")
            voice = st.checkbox("Voice is licensed, synthetic, or consented")
            media = st.checkbox("Products, property footage and backgrounds are authorized")
            if st.button("Start production", type="primary"):
                if not all([actor, face, voice, media]):
                    st.error("Confirm all rights items first.")
                else:
                    project = start_production(data, video_id)
                    project.rights.actor_consent = True
                    project.rights.face_identity_is_fictional_or_authorized = True
                    project.rights.voice_is_licensed_or_consented = True
                    project.rights.property_and_product_media_authorized = True
                    project.rights.ai_disclosure_required = True
                    save_project(project)
                    st.session_state.reality_project = project
                    st.session_state.bridge_video_id = video_id
                    st.switch_page("pages/2_Reality_Pipeline.py")
        else:
            if st.button("Open production", type="primary"):
                project = start_production(data, video_id)
                st.session_state.reality_project = project
                st.session_state.bridge_video_id = video_id
                st.switch_page("pages/2_Reality_Pipeline.py")

        if video.get("rendered_path") and Path(video["rendered_path"]).exists():
            st.success("The MP4 is connected and ready to publish.")
            st.video(video["rendered_path"])
    else:
        st.info("Add your first Sofia video.")

with p:
    ready = [v for v in data["videos"] if v["status"] in ["READY", "PUBLISHED"]]
    if not ready:
        st.info("Rendered videos appear here automatically when you return from Reality Pipeline.")
    else:
        video_id = st.selectbox("Video", [v["id"] for v in ready], format_func=lambda x: find_video(data, x)["title"], key="publish_select")
        video = find_video(data, video_id)
        if video.get("rendered_path") and Path(video["rendered_path"]).exists():
            st.video(video["rendered_path"])
        with st.form("publish"):
            url = st.text_input("Published link", value=video.get("published_url") or "")
            when = st.date_input("Published date", date.today())
            done = st.form_submit_button("Mark published", type="primary")
        if done:
            mark_published(data, video_id, url, when)
            st.rerun()

with a:
    published = [v for v in data["videos"] if v["status"] == "PUBLISHED"]
    if not published:
        st.info("Publish a video first.")
    else:
        video_id = st.selectbox("Published video", [v["id"] for v in published], format_func=lambda x: find_video(data, x)["title"], key="analytics_select")
        video = find_video(data, video_id)
        with st.form("analytics"):
            views = st.number_input("Views after 72 hours", min_value=0, value=1000)
            retention = st.number_input("Retention %", 0.0, 100.0, 45.0)
            completion = st.number_input("Completion %", 0.0, 100.0, 25.0)
            shares = st.number_input("Shares", min_value=0, value=10)
            followers = st.number_input("Followers gained", min_value=0, value=5)
            revenue = st.number_input("Actual income (€)", min_value=0.0, value=0.0)
            cost = st.number_input("Actual cost (€)", min_value=0.0, value=float(video.get("production_cost_eur", 0.0)))
            calculate = st.form_submit_button("Save result and decide", type="primary")
        if calculate:
            st.session_state.latest_result = save_analytics(data, video_id, views, retention, completion, shares, followers, revenue, cost)
        result = st.session_state.get("latest_result")
        if result:
            x1, x2, x3 = st.columns(3)
            x1.metric("Growth", result["growth_score"])
            x2.metric("Profit", f"€{result['profit_eur']:,.2f}")
            x3.metric("Decision", result["decision"])
    if data["tests"]:
        st.dataframe(data["tests"], use_container_width=True, hide_index=True)

with money:
    if data["income"]:
        st.dataframe(data["income"], use_container_width=True, hide_index=True)
    with st.form("income"):
        character = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA), key="money_character")
        source = st.selectbox("Source", ["TikTok", "YouTube", "Affiliate", "Sponsor", "Property lead", "Client service"])
        amount = st.number_input("Amount (€)", min_value=0.0, value=0.0)
        when = st.date_input("Date", date.today(), key="money_date")
        note = st.text_input("Note")
        record = st.form_submit_button("Record income", type="primary")
    if record and amount > 0:
        data["income"].append({"character": character, "source": source, "amount_eur": float(amount), "date": when.isoformat(), "note": note.strip()})
        save_data(data)
        st.rerun()
