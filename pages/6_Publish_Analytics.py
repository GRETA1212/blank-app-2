from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from creator_os import load_data as load_os_data, record_analytics, record_publication
from studio_bridge import find_video, load_data as load_studio_data
from upload_post_connector import SUPPORTED_VIDEO_PLATFORMS, UploadPostConnector


st.set_page_config(page_title="Publish & Analytics", page_icon="🚀", layout="wide")
st.title("🚀 Publish & Analytics")
st.caption("One connected publishing service for TikTok, YouTube, Instagram and the rest of the creator network.")

try:
    if not os.getenv("UPLOAD_POST_API_KEY") and "UPLOAD_POST_API_KEY" in st.secrets:
        os.environ["UPLOAD_POST_API_KEY"] = str(st.secrets["UPLOAD_POST_API_KEY"])
except FileNotFoundError:
    pass

connector = UploadPostConnector()
studio_data = load_studio_data()
os_data = load_os_data()

st.subheader("Publishing service")
if connector.configured:
    st.success("Upload-Post API is configured.")
else:
    st.error("Add UPLOAD_POST_API_KEY to .streamlit/secrets.toml or the environment.")

profile = st.text_input(
    "Creator profile username",
    value=os.getenv("UPLOAD_POST_PROFILE", "sofia"),
    help="This is the Upload-Post profile that owns the connected TikTok, YouTube and Instagram accounts.",
)

connect_left, connect_right = st.columns(2)
with connect_left:
    if st.button("Create profile", use_container_width=True, disabled=not connector.configured):
        try:
            st.json(connector.create_profile(profile))
        except Exception as error:
            st.error(str(error))
with connect_right:
    if st.button("Generate account-connection link", use_container_width=True, disabled=not connector.configured):
        try:
            result = connector.connection_link(
                profile,
                platforms=["tiktok", "youtube", "instagram"],
                language="en",
            )
            st.session_state["upload_post_connection"] = result
        except Exception as error:
            st.error(str(error))

connection = st.session_state.get("upload_post_connection")
if connection:
    connection_url = (
        connection.get("url")
        or connection.get("connection_url")
        or connection.get("connect_url")
        or (connection.get("data") or {}).get("url")
        or (connection.get("data") or {}).get("connection_url")
    )
    if connection_url:
        st.link_button("Open secure account connection", connection_url, use_container_width=True)
    else:
        st.json(connection)

rendered = [
    item
    for item in studio_data["videos"]
    if item.get("rendered_path") and Path(item["rendered_path"]).exists()
]
if not rendered:
    st.info("Render a master MP4 in Reality Pipeline first.")
    st.stop()

video_id = st.selectbox(
    "Master video",
    [item["id"] for item in rendered],
    format_func=lambda value: f"{find_video(studio_data, value)['character']} — {find_video(studio_data, value)['title']}",
)
video = find_video(studio_data, video_id)
video_path = Path(video["rendered_path"])
st.video(str(video_path))

publish_tab, status_tab, analytics_tab = st.tabs(["Publish", "Status & Schedule", "Analytics"])

with publish_tab:
    selected_platforms = st.multiselect(
        "Platforms",
        SUPPORTED_VIDEO_PLATFORMS,
        default=["tiktok", "youtube", "instagram"],
    )
    title = st.text_input("Title", value=video["title"][:100])
    description = st.text_area(
        "Description / caption",
        value=f"{video['title']}\n\n#virtualcreator #aigenerated",
        height=140,
    )
    tags = st.text_input("YouTube tags", value="shorts, virtual creator, AI generated")

    st.markdown("#### Publishing safety")
    safety_a, safety_b, safety_c = st.columns(3)
    ai_generated = safety_a.checkbox("Mark as AI-generated", value=True)
    paid_placement = safety_b.checkbox("Paid product placement", value=False)
    queue_only = safety_c.checkbox("Add to posting queue", value=True)

    st.markdown("#### Platform behavior")
    behavior_a, behavior_b, behavior_c = st.columns(3)
    youtube_privacy = behavior_a.selectbox("YouTube privacy", ["private", "unlisted", "public"], index=0)
    tiktok_mode = behavior_b.selectbox("TikTok mode", ["MEDIA_UPLOAD", "DIRECT_POST"], index=0)
    tiktok_privacy = behavior_c.selectbox(
        "TikTok privacy",
        ["SELF_ONLY", "FOLLOWER_OF_CREATOR", "MUTUAL_FOLLOW_FRIENDS", "PUBLIC_TO_EVERYONE"],
        index=0,
    )

    schedule_enabled = st.checkbox("Schedule for later")
    scheduled_date = None
    if schedule_enabled:
        scheduled_day = st.date_input("Publishing date")
        scheduled_time = st.time_input("Publishing time")
        scheduled_date = datetime.combine(scheduled_day, scheduled_time).isoformat()
    timezone = st.text_input("Timezone", value="Europe/Skopje")
    autogenerate = st.checkbox("Let Upload-Post generate native platform copy", value=False)

    if st.button("Send to selected platforms", type="primary", use_container_width=True, disabled=not connector.configured):
        try:
            result = connector.publish_video(
                video_path,
                username=profile,
                platforms=selected_platforms,
                title=title,
                description=description,
                scheduled_date=scheduled_date,
                timezone=timezone,
                queue_only=queue_only,
                youtube_tags=[item.strip() for item in tags.split(",") if item.strip()],
                youtube_privacy=youtube_privacy,
                tiktok_mode=tiktok_mode,
                tiktok_privacy=tiktok_privacy,
                is_ai_generated=ai_generated,
                has_paid_product_placement=paid_placement,
                autogenerate_copy=autogenerate,
                language_code=video.get("language", "English")[:2].lower(),
            )
            request_id = result.get("request_id") or (result.get("data") or {}).get("request_id")
            job_id = result.get("job_id") or (result.get("data") or {}).get("job_id")
            record_publication(
                os_data,
                video_id=video_id,
                platform=",".join(selected_platforms),
                external_id=request_id or job_id,
                url=None,
                status="QUEUED" if queue_only or schedule_enabled else "SUBMITTED",
                metadata=result,
            )
            st.success("Publishing request accepted.")
            st.json(result)
        except Exception as error:
            st.error(str(error))

with status_tab:
    publications = [item for item in os_data["publications"] if item.get("video_id") == video_id]
    if not publications:
        st.info("No publishing requests have been recorded for this video.")
    else:
        st.dataframe(publications, use_container_width=True, hide_index=True)
        publication_ids = [item["id"] for item in publications]
        selected_publication_id = st.selectbox("Publishing request", publication_ids)
        publication = next(item for item in publications if item["id"] == selected_publication_id)
        metadata = publication.get("metadata") or {}
        request_id = metadata.get("request_id") or (metadata.get("data") or {}).get("request_id")
        job_id = metadata.get("job_id") or (metadata.get("data") or {}).get("job_id")
        if st.button("Refresh request status", disabled=not connector.configured):
            try:
                st.json(connector.get_status(request_id=request_id, job_id=job_id))
            except Exception as error:
                st.error(str(error))

    if st.button("Show scheduled posts", disabled=not connector.configured):
        try:
            st.json(connector.list_scheduled())
        except Exception as error:
            st.error(str(error))

    if st.button("Show upload history", disabled=not connector.configured):
        try:
            st.json(connector.get_history(page=1, limit=20))
        except Exception as error:
            st.error(str(error))

with analytics_tab:
    platforms = st.multiselect(
        "Analytics platforms",
        ["tiktok", "youtube", "instagram", "facebook", "linkedin", "x", "threads", "pinterest", "reddit"],
        default=["tiktok", "youtube", "instagram"],
        key="analytics_platforms",
    )
    if st.button("Fetch creator analytics", type="primary", disabled=not connector.configured):
        try:
            result = connector.get_profile_analytics(profile, platforms=platforms)
            record_analytics(
                os_data,
                {
                    "video_id": video_id,
                    "character": video["character"],
                    "platform": ",".join(platforms),
                    "profile": profile,
                    "raw": result,
                },
            )
            st.json(result)
        except Exception as error:
            st.error(str(error))

    publications = [item for item in os_data["publications"] if item.get("video_id") == video_id]
    post_requests = []
    for item in publications:
        metadata = item.get("metadata") or {}
        request_id = metadata.get("request_id") or (metadata.get("data") or {}).get("request_id")
        if request_id:
            post_requests.append(request_id)
    if post_requests:
        selected_request_id = st.selectbox("Post request for per-post analytics", post_requests)
        if st.button("Fetch post analytics", disabled=not connector.configured):
            try:
                result = connector.get_post_analytics(selected_request_id)
                st.json(result)
            except Exception as error:
                st.error(str(error))
