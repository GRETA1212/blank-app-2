from __future__ import annotations

import streamlit as st

from niche_manager import get_niche, update_niche
from creator_studio import SEED_CHARACTERS


st.set_page_config(page_title="Niche Manager", page_icon="🎯", layout="wide")
st.title("🎯 Niche Manager")
st.caption("Define what each creator talks about, who the audience is, what can be monetized, and which topics must be avoided.")

character = st.selectbox("Creator", list(SEED_CHARACTERS))
profile = get_niche(character)

with st.form(f"niche_{character}"):
    c1, c2 = st.columns(2)
    with c1:
        primary_niche = st.text_input("Primary niche", value=profile["primary_niche"])
        subtopics = st.text_area("Subtopics", value=", ".join(profile["subtopics"]), height=120)
        keywords = st.text_area("Trend keywords", value=", ".join(profile["keywords"]), height=120)
        audience = st.text_area("Target audience", value=profile["audience"], height=100)
        competitors = st.text_area("Competitor usernames or channels", value=", ".join(profile["competitors"]), height=120)
    with c2:
        products = st.text_area("Products and revenue opportunities", value=", ".join(profile["products"]), height=120)
        avoid_topics = st.text_area("Topics and claims to avoid", value=", ".join(profile["avoid_topics"]), height=120)
        content_pillars = st.text_area("Content pillars", value=", ".join(profile["content_pillars"]), height=120)
        languages = st.text_input("Languages", value=", ".join(profile["languages"]))
        platforms = st.text_input("Platforms", value=", ".join(profile["platforms"]))
    saved = st.form_submit_button("Save niche profile", type="primary", use_container_width=True)

if saved:
    result = update_niche(
        character,
        {
            "primary_niche": primary_niche,
            "subtopics": subtopics,
            "keywords": keywords,
            "audience": audience,
            "competitors": competitors,
            "products": products,
            "avoid_topics": avoid_topics,
            "content_pillars": content_pillars,
            "languages": languages,
            "platforms": platforms,
        },
    )
    st.success("Niche profile saved.")
    st.json(result)

st.divider()
st.subheader("How this profile is used")
st.write(
    "Trend Radar uses the keywords and primary niche. Daily Planner uses the audience, content pillars, products, and avoid list when selecting ideas."
)
