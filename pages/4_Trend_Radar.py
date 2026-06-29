from __future__ import annotations

import os

import streamlit as st

from creator_os import add_trends, load_data, top_trends
from creator_studio import SEED_CHARACTERS
from justone_trend_source import JustOneTikTokSource
from niche_manager import get_niche
from trend_engine import GoogleTrendingNowSource, YouTubeTrendSource, manual_tiktok_trend, to_dicts


st.set_page_config(page_title="Trend Radar", page_icon="📡", layout="wide")
st.title("📡 Trend Radar")
st.caption("Discover content opportunities, score them for the creator's niche, and send the strongest topics to the daily planner.")

for secret_name in ["YOUTUBE_DATA_API_KEY", "JUSTONEAPI_TOKEN"]:
    try:
        if not os.getenv(secret_name) and secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
    except FileNotFoundError:
        pass

data = load_data()
character = st.selectbox("Creator", list(SEED_CHARACTERS))
niche_profile = get_niche(character)
niche = niche_profile["primary_niche"]
region = st.text_input("Region code", value="US", max_chars=2).upper()
keywords_text = st.text_input("Niche keywords", value=", ".join(niche_profile["keywords"]))
keywords = [item.strip() for item in keywords_text.split(",") if item.strip()]

summary_a, summary_b, summary_c = st.columns(3)
summary_a.metric("Niche", niche)
summary_b.metric("Subtopics", len(niche_profile["subtopics"]))
summary_c.metric("Competitors tracked", len(niche_profile["competitors"]))
if niche_profile["competitors"]:
    st.caption("Competitor watchlist: " + ", ".join(niche_profile["competitors"]))

source_a, source_b, source_c = st.columns(3)
with source_a:
    st.subheader("YouTube")
    query = st.text_input("YouTube search", value=f"{niche} tips")
    days = st.slider("Recent days", 1, 30, 14)
    max_results = st.slider("Videos to inspect", 5, 50, 20)
    if st.button("Fetch YouTube trends", type="primary", use_container_width=True):
        try:
            items = YouTubeTrendSource().search(
                query,
                niche=niche,
                niche_keywords=keywords,
                region=region,
                days=days,
                max_results=max_results,
            )
            added = add_trends(data, to_dicts(items))
            st.success(f"Added {added} new YouTube trend items.")
            st.rerun()
        except Exception as error:
            st.error(str(error))

with source_b:
    st.subheader("Google Trending Now")
    st.write("Uses Google's Trending Now RSS export and applies your niche score.")
    if st.button("Fetch Google trends", type="primary", use_container_width=True):
        try:
            items = GoogleTrendingNowSource().fetch(
                niche=niche,
                niche_keywords=keywords,
                region=region,
            )
            added = add_trends(data, to_dicts(items))
            st.success(f"Added {added} new Google trend items.")
            st.rerun()
        except Exception as error:
            st.error(str(error))

with source_c:
    st.subheader("TikTok data")
    tiktok_query = st.text_input("TikTok keyword", value=keywords[0] if keywords else niche)
    publish_time = st.selectbox(
        "Published",
        ["ONE_DAY", "ONE_WEEK", "ONE_MONTH", "THREE_MONTHS", "ALL"],
        index=1,
    )
    sort_type = st.selectbox("TikTok sort", ["MOST_LIKED", "RELEVANCE"])
    if st.button("Search TikTok through JustOneAPI", type="primary", use_container_width=True):
        try:
            items = JustOneTikTokSource().search(
                tiktok_query,
                niche=niche,
                niche_keywords=keywords,
                region=region,
                publish_time=publish_time,
                sort_type=sort_type,
            )
            added = add_trends(data, to_dicts(items))
            st.success(f"Added {added} new TikTok trend items.")
            st.rerun()
        except Exception as error:
            st.error(str(error))
    if not JustOneTikTokSource().configured:
        st.caption("Add JUSTONEAPI_TOKEN to enable structured TikTok search.")

st.divider()
st.subheader("Save a TikTok or competitor trend")
st.caption("Use TikTok Creative Center, your own feed, or a public competitor link. The app stores the observation without copying account cookies or bypassing platform controls.")
with st.form("manual_tiktok"):
    title = st.text_input("Trend, sound, hook, or format")
    url = st.text_input("Public TikTok, Creative Center, or competitor link")
    notes = st.text_area("Why it is working")
    c1, c2, c3 = st.columns(3)
    strength = c1.slider("Trend strength", 0, 100, 75)
    niche_fit = c2.slider("Niche fit", 0, 100, 85)
    monetization = c3.slider("Monetization", 0, 100, 65)
    c4, c5 = st.columns(2)
    originality = c4.slider("Original angle available", 0, 100, 70)
    ease = c5.slider("Production ease", 0, 100, 75)
    save = st.form_submit_button("Save trend", type="primary")
if save:
    if not title.strip():
        st.error("Enter a trend title.")
    else:
        item = manual_tiktok_trend(
            title,
            niche=niche,
            region=region,
            strength=strength,
            niche_fit=niche_fit,
            monetization=monetization,
            originality=originality,
            production_ease=ease,
            url=url.strip() or None,
            notes=notes,
        )
        add_trends(data, to_dicts([item]))
        st.success("Trend saved.")
        st.rerun()

st.divider()
st.subheader(f"Best opportunities for {character}")
items = top_trends(data, niche=niche, limit=50)
if not items:
    st.info("Fetch or save trends above.")
else:
    st.dataframe(
        [
            {
                "Score": item.get("score"),
                "Source": item.get("source"),
                "Topic": item.get("title"),
                "Strength": item.get("strength"),
                "Niche fit": item.get("niche_fit"),
                "Monetization": item.get("monetization"),
                "Region": item.get("region"),
                "Link": item.get("url") or "",
            }
            for item in items
        ],
        use_container_width=True,
        hide_index=True,
    )
