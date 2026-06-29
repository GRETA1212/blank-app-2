from __future__ import annotations

import os

import streamlit as st

from creator_os import add_trends, load_data, top_trends
from creator_studio import SEED_CHARACTERS
from trend_engine import GoogleTrendingNowSource, YouTubeTrendSource, manual_tiktok_trend, to_dicts


st.set_page_config(page_title="Trend Radar", page_icon="📡", layout="wide")
st.title("📡 Trend Radar")
st.caption("Discover content opportunities, score them for the creator's niche, and send the strongest topics to the daily planner.")

for secret_name in ["YOUTUBE_DATA_API_KEY"]:
    try:
        if not os.getenv(secret_name) and secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
    except FileNotFoundError:
        pass

data = load_data()
character = st.selectbox("Creator", list(SEED_CHARACTERS))
profile = SEED_CHARACTERS[character]
region = st.text_input("Region code", value="US", max_chars=2).upper()
default_keywords = {
    "Beauty": "makeup, skincare, beauty, eyeliner, lipstick, hair",
    "Real Estate": "apartment, house, property, interior, mortgage, renovation",
    "Mini Movies": "mystery, storytime, short film, romance, thriller, plot twist",
}.get(profile.niche, profile.niche)
keywords_text = st.text_input("Niche keywords", value=default_keywords)
keywords = [item.strip() for item in keywords_text.split(",") if item.strip()]

source_a, source_b = st.columns(2)
with source_a:
    st.subheader("YouTube")
    query = st.text_input("YouTube search", value=f"{profile.niche} tips")
    days = st.slider("Recent days", 1, 30, 14)
    max_results = st.slider("Videos to inspect", 5, 50, 20)
    if st.button("Fetch YouTube trends", type="primary", use_container_width=True):
        try:
            items = YouTubeTrendSource().search(
                query,
                niche=profile.niche,
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
                niche=profile.niche,
                niche_keywords=keywords,
                region=region,
            )
            added = add_trends(data, to_dicts(items))
            st.success(f"Added {added} new Google trend items.")
            st.rerun()
        except Exception as error:
            st.error(str(error))

st.divider()
st.subheader("Save a TikTok trend")
st.caption("Use TikTok Creative Center or your feed, then save the topic here. This avoids unauthorized scraping.")
with st.form("manual_tiktok"):
    title = st.text_input("Trend, sound, hook, or format")
    url = st.text_input("TikTok or Creative Center link")
    notes = st.text_area("Why it is working")
    c1, c2, c3 = st.columns(3)
    strength = c1.slider("Trend strength", 0, 100, 75)
    niche_fit = c2.slider("Niche fit", 0, 100, 85)
    monetization = c3.slider("Monetization", 0, 100, 65)
    c4, c5 = st.columns(2)
    originality = c4.slider("Original angle available", 0, 100, 70)
    ease = c5.slider("Production ease", 0, 100, 75)
    save = st.form_submit_button("Save TikTok trend", type="primary")
if save:
    if not title.strip():
        st.error("Enter a trend title.")
    else:
        item = manual_tiktok_trend(
            title,
            niche=profile.niche,
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
        st.success("TikTok trend saved.")
        st.rerun()

st.divider()
st.subheader(f"Best opportunities for {character}")
items = top_trends(data, niche=profile.niche, limit=50)
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
