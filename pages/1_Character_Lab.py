from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict

import streamlit as st

from character_lab import (
    DEFAULT_CHARACTER_DNA,
    REFERENCE_SLOTS,
    CharacterDNA,
    build_scene_direction,
    calculate_consistency_score,
    list_assets,
    load_character,
    save_asset,
    save_character,
)


st.set_page_config(page_title="Character Lab", page_icon="🧬", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
      .character-hero {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 18px;
        padding: 22px;
        background: linear-gradient(135deg, rgba(236,72,153,.16), rgba(99,102,241,.16));
        margin-bottom: 18px;
      }
      .rule-card {
        border: 1px solid rgba(255,255,255,.11);
        border-radius: 14px;
        padding: 14px;
        min-height: 120px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="character-hero">
      <h1>🧬 Character Lab</h1>
      <p>Create a permanent face, voice, behavior and movement system for every virtual creator.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

character_name = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA.keys()))
profile_key = f"character_lab_profile_{character_name}"

if profile_key not in st.session_state:
    st.session_state[profile_key] = load_character(character_name)

profile: CharacterDNA = st.session_state[profile_key]

top_a, top_b, top_c, top_d = st.columns(4)
top_a.metric("Character", profile.name)
top_b.metric("Niche", profile.niche)
top_c.metric("Profile version", profile.version)
top_d.metric("Reference slots", len(REFERENCE_SLOTS))

tab_identity, tab_refs, tab_voice, tab_world, tab_director, tab_check = st.tabs(
    [
        "Identity DNA",
        "Reference Pack",
        "Voice DNA",
        "World & Movement",
        "Scene Director",
        "Consistency Gate",
    ]
)

with tab_identity:
    st.subheader("Permanent appearance and behavior")
    st.caption("These values should remain stable across every generated video unless a story explicitly changes them.")

    with st.form(f"identity_form_{character_name}"):
        c1, c2 = st.columns(2)
        with c1:
            apparent_age = st.number_input("Apparent age", min_value=18, max_value=80, value=profile.appearance.apparent_age)
            skin_tone = st.text_input("Skin tone and texture", value=profile.appearance.skin_tone)
            eye_color = st.text_input("Eye color", value=profile.appearance.eye_color)
            face_shape = st.text_input("Face shape", value=profile.appearance.face_shape)
            hair = st.text_area("Hair", value=profile.appearance.hair)
            signature_item = st.text_input("Signature item", value=profile.appearance.signature_item)
            body_posture = st.text_area("Body and posture", value=profile.appearance.body_and_posture)
        with c2:
            distinguishing = st.text_area(
                "Distinguishing features — one per line",
                value="\n".join(profile.appearance.distinguishing_features),
                height=120,
            )
            palette = st.text_input("Color palette — comma separated", value=", ".join(profile.appearance.color_palette))
            personality = st.text_input("Personality — comma separated", value=", ".join(profile.behavior.personality))
            gestures = st.text_area("Signature gestures — one per line", value="\n".join(profile.behavior.gestures), height=130)
            habits = st.text_area("Habits — one per line", value="\n".join(profile.behavior.habits), height=100)
            catchphrase = st.text_input("Catchphrase", value=profile.behavior.catchphrase)
        save_identity = st.form_submit_button("Save identity DNA", type="primary")

    if save_identity:
        edited = deepcopy(profile)
        edited.appearance.apparent_age = int(apparent_age)
        edited.appearance.skin_tone = skin_tone.strip()
        edited.appearance.eye_color = eye_color.strip()
        edited.appearance.face_shape = face_shape.strip()
        edited.appearance.hair = hair.strip()
        edited.appearance.signature_item = signature_item.strip()
        edited.appearance.body_and_posture = body_posture.strip()
        edited.appearance.distinguishing_features = [line.strip() for line in distinguishing.splitlines() if line.strip()]
        edited.appearance.color_palette = [item.strip() for item in palette.split(",") if item.strip()]
        edited.behavior.personality = [item.strip() for item in personality.split(",") if item.strip()]
        edited.behavior.gestures = [line.strip() for line in gestures.splitlines() if line.strip()]
        edited.behavior.habits = [line.strip() for line in habits.splitlines() if line.strip()]
        edited.behavior.catchphrase = catchphrase.strip()
        edited.version += 1
        destination = save_character(edited)
        st.session_state[profile_key] = edited
        profile = edited
        st.success(f"Saved version {edited.version} to {destination}.")

    st.markdown("### Identity lock")
    i1, i2, i3 = st.columns(3)
    with i1:
        st.markdown(
            f"""
            <div class="rule-card">
              <b>Face</b><br>
              {profile.appearance.face_shape}<br>
              {profile.appearance.eye_color} eyes<br>
              {profile.appearance.hair}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with i2:
        st.markdown(
            f"""
            <div class="rule-card">
              <b>Recognizable markers</b><br>
              {'<br>'.join(profile.appearance.distinguishing_features)}<br>
              Signature: {profile.appearance.signature_item}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with i3:
        st.markdown(
            f"""
            <div class="rule-card">
              <b>Behavior</b><br>
              {', '.join(profile.behavior.personality)}<br>
              “{profile.behavior.catchphrase}”
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab_refs:
    st.subheader("Reference image pack")
    st.caption(
        "Upload several views of the same approved character. These local files are ignored by Git and stay in the storage folder."
    )

    slot = st.selectbox("Reference slot", REFERENCE_SLOTS)
    uploaded_reference = st.file_uploader(
        "Upload PNG, JPG or WEBP",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"reference_upload_{character_name}",
    )

    if uploaded_reference is not None:
        st.image(uploaded_reference, caption=f"{character_name} — {slot}", width=320)
        if st.button("Save reference image", type="primary"):
            try:
                path = save_asset(
                    character_name,
                    "reference_image",
                    uploaded_reference.name,
                    uploaded_reference.getvalue(),
                    slot=slot,
                )
                st.success(f"Saved: {path}")
            except ValueError as error:
                st.error(str(error))

    st.markdown("### Required reference checklist")
    reference_checks = {
        "Front neutral": "Defines facial geometry without expression.",
        "Three-quarter left and right": "Protects identity when the camera angle changes.",
        "Left and right profile": "Protects nose, lips, chin and hair silhouette.",
        "Full body": "Locks body proportions and posture.",
        "Expressions": "Smile, surprise, concern and speaking mouth shapes.",
        "Standard outfits": "Prevents wardrobe drift across a recurring series.",
    }
    for label, description in reference_checks.items():
        st.checkbox(f"{label} — {description}", key=f"{character_name}_ref_{label}")

    assets = list_assets(character_name)
    reference_assets = [asset for asset in assets if asset["relative_path"].startswith("references")]
    if reference_assets:
        st.markdown("### Stored reference assets")
        st.dataframe(reference_assets, use_container_width=True, hide_index=True)
    else:
        st.info("No local reference images have been saved yet.")

with tab_voice:
    st.subheader("Permanent voice identity")
    st.warning(
        "Use a licensed synthetic voice or a consenting voice actor. Do not clone celebrities or another real person without permission."
    )

    with st.form(f"voice_form_{character_name}"):
        v1, v2 = st.columns(2)
        with v1:
            primary_language = st.text_input("Primary language", value=profile.voice.primary_language)
            secondary_languages = st.text_input(
                "Secondary languages — comma separated",
                value=", ".join(profile.voice.secondary_languages),
            )
            accent = st.text_area("Accent direction", value=profile.voice.accent)
            pitch = st.text_input("Pitch and tone", value=profile.voice.pitch)
            words_per_minute = st.number_input(
                "Words per minute",
                min_value=70,
                max_value=220,
                value=profile.voice.words_per_minute,
            )
        with v2:
            energy = st.text_area("Energy", value=profile.voice.energy)
            pause_style = st.text_area("Pause and rhythm", value=profile.voice.pause_style)
            emotions = st.text_input(
                "Emotional modes — comma separated",
                value=", ".join(profile.voice.emotional_range),
            )
            provider = st.text_input("Voice provider", value=profile.voice.provider)
            provider_voice_id = st.text_input("Provider voice ID", value=profile.voice.provider_voice_id)
            consent_confirmed = st.checkbox(
                "I confirm this voice is licensed, synthetic, or recorded by a consenting actor.",
                value=False,
            )
        save_voice = st.form_submit_button("Save voice DNA", type="primary")

    if save_voice:
        if not consent_confirmed:
            st.error("Confirm voice rights before saving a provider voice.")
        else:
            edited = deepcopy(profile)
            edited.voice.primary_language = primary_language.strip()
            edited.voice.secondary_languages = [item.strip() for item in secondary_languages.split(",") if item.strip()]
            edited.voice.accent = accent.strip()
            edited.voice.pitch = pitch.strip()
            edited.voice.words_per_minute = int(words_per_minute)
            edited.voice.energy = energy.strip()
            edited.voice.pause_style = pause_style.strip()
            edited.voice.emotional_range = [item.strip() for item in emotions.split(",") if item.strip()]
            edited.voice.provider = provider.strip() or "Not configured"
            edited.voice.provider_voice_id = provider_voice_id.strip()
            edited.version += 1
            destination = save_character(edited)
            st.session_state[profile_key] = edited
            profile = edited
            st.success(f"Voice DNA saved to {destination}.")

    voice_upload = st.file_uploader(
        "Optional licensed voice sample",
        type=["mp3", "wav", "m4a", "aac"],
        key=f"voice_upload_{character_name}",
    )
    voice_rights = st.checkbox(
        "I have permission to use this uploaded voice sample.",
        key=f"voice_rights_{character_name}",
    )
    if voice_upload is not None and st.button("Save voice sample"):
        if not voice_rights:
            st.error("Confirm permission before saving the sample.")
        else:
            try:
                path = save_asset(
                    character_name,
                    "voice_sample",
                    voice_upload.name,
                    voice_upload.getvalue(),
                )
                st.success(f"Saved: {path}")
                st.audio(voice_upload)
            except ValueError as error:
                st.error(str(error))

    st.markdown("### Voice direction summary")
    st.code(
        f"""
Character: {profile.name}
Primary language: {profile.voice.primary_language}
Accent: {profile.voice.accent}
Pitch: {profile.voice.pitch}
Pace: {profile.voice.words_per_minute} words/minute
Energy: {profile.voice.energy}
Pauses: {profile.voice.pause_style}
Emotions: {", ".join(profile.voice.emotional_range)}
        """.strip(),
        language=None,
    )

with tab_world:
    st.subheader("Recurring world and movement library")
    left, middle, right = st.columns(3)
    with left:
        st.markdown("#### Wardrobe")
        for item in profile.wardrobe:
            st.markdown(f"**{item['name']}**  \n{item['description']}")
    with middle:
        st.markdown("#### Locations")
        for item in profile.locations:
            st.markdown(f"**{item['name']}**  \n{item['description']}")
    with right:
        st.markdown("#### Actions")
        for item in profile.actions:
            st.markdown(f"**{item['name']}**  \n{item['description']}")

    st.divider()
    st.markdown("### How movement becomes believable")
    movement_rules = [
        "The face reacts a fraction of a second before dialogue begins.",
        "Hands interact with real objects instead of making generic gestures.",
        "Blinking, breathing and eye-line changes are subtle and irregular.",
        "The character uses niche-specific actions: brushes for Sofia, doors and floor plans for Elena, evidence and hiding for Luna.",
        "Camera changes are motivated by an action, reveal or emotional beat.",
        "The character enters, crosses and exits locations with stable room geography.",
    ]
    for rule in movement_rules:
        st.write(f"• {rule}")

with tab_director:
    st.subheader("Direct one performable scene")
    st.caption("The output can later be sent to image, video, voice and lip-sync providers.")

    action_names = [item["name"] for item in profile.actions]
    location_names = [item["name"] for item in profile.locations]
    wardrobe_names = [item["name"] for item in profile.wardrobe]

    with st.form(f"scene_director_{character_name}"):
        d1, d2 = st.columns(2)
        with d1:
            dialogue = st.text_area(
                "Dialogue",
                value=profile.behavior.catchphrase,
                height=110,
            )
            emotion = st.selectbox("Emotion", profile.voice.emotional_range)
            action_name = st.selectbox("Action", action_names)
            duration_seconds = st.slider("Duration in seconds", 2.0, 20.0, 6.0, 0.5)
        with d2:
            location_name = st.selectbox("Location", location_names)
            wardrobe_name = st.selectbox("Wardrobe", wardrobe_names)
            camera = st.selectbox(
                "Camera",
                [
                    "close-up, eye level, gentle natural handheld movement",
                    "medium shot, eye level, locked camera",
                    "wide establishing shot, slow controlled push-in",
                    "over-the-shoulder detail shot",
                    "tracking shot following the character",
                ],
            )
        direct_scene = st.form_submit_button("Generate scene direction", type="primary")

    if direct_scene:
        try:
            scene = build_scene_direction(
                profile,
                dialogue=dialogue.strip(),
                emotion=emotion,
                action_name=action_name,
                location_name=location_name,
                wardrobe_name=wardrobe_name,
                camera=camera,
                duration_seconds=float(duration_seconds),
            )
            st.session_state[f"scene_package_{character_name}"] = scene
        except ValueError as error:
            st.error(str(error))

    scene = st.session_state.get(f"scene_package_{character_name}")
    if scene:
        st.markdown("#### Visual generation prompt")
        st.text_area("Visual prompt", value=scene["visual_prompt"], height=220)
        st.markdown("#### Performance direction")
        st.text_area("Performance direction", value=scene["performance_direction"], height=150)
        st.markdown("#### Voice direction")
        st.text_area("Voice direction", value=scene["voice_direction"], height=140)
        st.markdown("#### Negative prompt")
        st.text_area("Negative prompt", value=scene["negative_prompt"], height=100)
        st.download_button(
            "Download scene package",
            data=json.dumps(scene, ensure_ascii=False, indent=2),
            file_name=f"{profile.name.lower()}-scene-package.json",
            mime="application/json",
        )

with tab_check:
    st.subheader("Pre-publish consistency gate")
    st.caption("Reject a scene when the character identity, voice, world or physical interaction drifts.")

    check_definitions = {
        "face": "Face shape, age and distinguishing markers match the approved references.",
        "eyes": f"Eye color remains {profile.appearance.eye_color}.",
        "hair": f"Hair matches: {profile.appearance.hair}.",
        "signature": f"Signature item is correct when appropriate: {profile.appearance.signature_item}.",
        "voice": "Voice ID, accent, pace and emotion match the Voice DNA.",
        "hands": "Hands and object interactions are anatomically believable.",
        "wardrobe": "Wardrobe matches one approved set.",
        "location": "Doors, windows, furniture and geography remain stable between shots.",
        "facts": "Products, prices, dimensions and story facts are verified and consistent.",
        "rights": "Voice, visuals, audio and property/product media are licensed or permitted.",
        "disclosure": "AI-generated-content disclosure is prepared where required.",
    }

    results: dict[str, bool] = {}
    for key, text in check_definitions.items():
        results[key] = st.checkbox(text, key=f"consistency_{character_name}_{key}")

    score = calculate_consistency_score(results)
    c1, c2, c3 = st.columns(3)
    c1.metric("Consistency score", f"{score['score']}%")
    c2.metric("Checks passed", f"{score['passed']}/{score['total']}")
    c3.metric("Decision", score["status"])

    if score["status"] == "APPROVED":
        st.success("Scene is ready for human approval and export.")
    elif score["status"] == "FIX MINOR ISSUES":
        st.warning("Correct the unchecked items before publishing.")
    else:
        st.error("Reject this scene and regenerate the failed elements.")

    st.download_button(
        "Download character DNA",
        data=json.dumps(asdict(profile), ensure_ascii=False, indent=2),
        file_name=f"{profile.name.lower()}-character-dna.json",
        mime="application/json",
    )
