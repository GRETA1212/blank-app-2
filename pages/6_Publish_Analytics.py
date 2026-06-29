from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from creator_os import load_data as load_os_data, record_analytics, record_publication
from platform_connectors import TikTokDraftConnector, YouTubeConnector, publication_readiness
from providers import ProviderError
from studio_bridge import find_video, load_data as load_studio_data


st.set_page_config(page_title="Publish & Analytics", page_icon="🚀", layout="wide")
st.title("🚀 Publish & Analytics")
st.caption("Upload approved masters, keep TikTok review in the loop, and feed performance data back into tomorrow's plan.")

for secret_name in ["YOUTUBE_OAUTH_TOKEN_JSON", "TIKTOK_ACCESS_TOKEN"]:
    try:
        if not os.getenv(secret_name) and secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
    except FileNotFoundError:
        pass

studio_data = load_studio_data()
os_data = load_os_data()

st.subheader("Connection readiness")
st.dataframe(
    [
        {
            "Platform": item["platform"],
            "Ready": "Yes" if item["configured"] else "No",
            "Mode": item["mode"],
            "Missing": ", ".join(item["missing"]),
        }
        for item in publication_readiness()
    ],
    use_container_width=True,
    hide_index=True,
)

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

publish_tab, analytics_tab = st.tabs(["Publish", "Analytics"])

with publish_tab:
    title = st.text_input("Title", value=video["title"][:100])
    description = st.text_area(
        "Description / caption",
        value=f"{video['title']}\n\n#shorts #virtualcreator #aigenerated",
        height=140,
    )
    tags = st.text_input("YouTube tags", value="shorts, virtual creator, AI generated")
    st.warning("YouTube uploads start as private. TikTok uploads go to the creator inbox for review and final posting.")
    left, right = st.columns(2)
    with left:
        if st.button("Upload privately to YouTube", type="primary", use_container_width=True):
            try:
                result = YouTubeConnector().upload_video(
                    video_path,
                    title=title,
                    description=description,
                    tags=[item.strip() for item in tags.split(",") if item.strip()],
                    privacy_status="private",
                    contains_synthetic_media=True,
                )
                record_publication(
                    os_data,
                    video_id=video_id,
                    platform="YouTube",
                    external_id=result.get("video_id"),
                    url=result.get("url"),
                    status="PRIVATE_REVIEW",
                    metadata=result,
                )
                st.success(f"Uploaded privately: {result.get('url')}")
            except Exception as error:
                st.error(str(error))
    with right:
        if st.button("Send draft to TikTok inbox", type="primary", use_container_width=True):
            try:
                result = TikTokDraftConnector().upload_draft(video_path)
                record_publication(
                    os_data,
                    video_id=video_id,
                    platform="TikTok",
                    external_id=result.get("publish_id"),
                    url=None,
                    status=result.get("status", "UPLOADED_TO_INBOX"),
                    metadata=result,
                )
                st.success("Draft sent. Open TikTok, tap the inbox notification, review, edit, and publish.")
            except Exception as error:
                st.error(str(error))

    publications = [item for item in os_data["publications"] if item.get("video_id") == video_id]
    if publications:
        st.dataframe(publications, use_container_width=True, hide_index=True)
        tiktok_records = [item for item in publications if item.get("platform") == "TikTok" and item.get("external_id")]
        if tiktok_records:
            selected_publish = st.selectbox("TikTok draft to refresh", [item["external_id"] for item in tiktok_records])
            if st.button("Refresh TikTok status"):
                try:
                    status = TikTokDraftConnector().get_status(selected_publish)
                    st.json(status)
                except Exception as error:
                    st.error(str(error))

with analytics_tab:
    st.subheader("YouTube Analytics")
    start = st.date_input("Start date", date.today() - timedelta(days=30))
    end = st.date_input("End date", date.today())
    youtube_publications = [
        item for item in os_data["publications"] if item.get("video_id") == video_id and item.get("platform") == "YouTube"
    ]
    youtube_external_id = youtube_publications[-1].get("external_id") if youtube_publications else None
    if st.button("Fetch YouTube performance", type="primary"):
        try:
            response = YouTubeConnector().analytics(start_date=start, end_date=end, video_id=youtube_external_id)
            headers = [item.get("name") for item in response.get("columnHeaders", [])]
            rows = response.get("rows", [])
            st.dataframe([dict(zip(headers, row)) for row in rows], use_container_width=True, hide_index=True)
            record_analytics(
                os_data,
                {
                    "video_id": video_id,
                    "character": video["character"],
                    "platform": "YouTube",
                    "external_id": youtube_external_id,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "raw": response,
                },
            )
        except Exception as error:
            st.error(str(error))

    st.subheader("Manual TikTok result")
    with st.form("manual_tiktok_metrics"):
        views = st.number_input("Views", min_value=0, value=0)
        retention = st.number_input("Average retention %", 0.0, 100.0, 0.0)
        completion = st.number_input("Completion %", 0.0, 100.0, 0.0)
        likes = st.number_input("Likes", min_value=0, value=0)
        comments = st.number_input("Comments", min_value=0, value=0)
        shares = st.number_input("Shares", min_value=0, value=0)
        followers = st.number_input("Followers gained", min_value=0, value=0)
        revenue = st.number_input("Revenue (€)", min_value=0.0, value=0.0)
        save = st.form_submit_button("Save TikTok result", type="primary")
    if save:
        growth_score = round(
            retention * 0.35
            + completion * 0.25
            + min(100.0, shares / max(views, 1) * 1000 / 20 * 100) * 0.20
            + min(100.0, followers / max(views, 1) * 1000 / 20 * 100) * 0.20,
            1,
        )
        record_analytics(
            os_data,
            {
                "video_id": video_id,
                "character": video["character"],
                "platform": "TikTok",
                "views": int(views),
                "retention_percent": float(retention),
                "completion_percent": float(completion),
                "likes": int(likes),
                "comments": int(comments),
                "shares": int(shares),
                "followers_gained": int(followers),
                "revenue_eur": float(revenue),
                "growth_score": growth_score,
            },
        )
        st.success(f"TikTok result saved. Growth score: {growth_score}")
