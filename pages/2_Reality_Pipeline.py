from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import streamlit as st

from character_lab import DEFAULT_CHARACTER_DNA, CharacterDNA, load_character
from realism_pipeline import (
    RealismProject,
    RightsRecord,
    ShotSpec,
    build_realism_manifest,
    default_shot_plan,
    ensure_project_structure,
    evaluate_realism_gate,
    export_project_package,
    find_ffmpeg,
    generate_srt,
    list_projects,
    load_project,
    ordered_generated_shots,
    render_vertical_video,
    safe_project_id,
    save_manifest_and_subtitles,
    save_project,
    save_project_asset,
    utc_now_iso,
)


st.set_page_config(page_title="Reality Pipeline", page_icon="🎥", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.3rem; padding-bottom: 3rem;}
      .reality-hero {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 18px;
        padding: 22px;
        background: linear-gradient(135deg, rgba(16,185,129,.16), rgba(14,165,233,.15));
        margin-bottom: 18px;
      }
      .pipeline-card {
        border: 1px solid rgba(255,255,255,.11);
        border-radius: 14px;
        padding: 14px;
        min-height: 145px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="reality-hero">
      <h1>🎥 Reality Pipeline</h1>
      <p>Turn a consenting human performance into a consistent fictional digital creator, then assemble and quality-check the final vertical video.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.warning(
    "This workflow is for fictional or authorized identities only. It requires actor consent, voice rights, media rights and AI disclosure where required."
)

if "reality_project" not in st.session_state:
    st.session_state.reality_project = None

saved_projects = list_projects()
sidebar_choice = st.sidebar.selectbox(
    "Project",
    ["Create a new project", *[item["project_id"] for item in saved_projects]],
)

if sidebar_choice != "Create a new project":
    current = st.session_state.reality_project
    if current is None or current.project_id != sidebar_choice:
        try:
            st.session_state.reality_project = load_project(sidebar_choice)
        except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as error:
            st.sidebar.error(str(error))

project: RealismProject | None = st.session_state.reality_project

setup_tab, assets_tab, shots_tab, package_tab, assembly_tab, qa_tab = st.tabs(
    [
        "1. Project & Rights",
        "2. Performance Assets",
        "3. Shot Director",
        "4. Provider Package",
        "5. Assemble MP4",
        "6. Reality Gate",
    ]
)

with setup_tab:
    st.subheader("Create the realism project")
    st.caption(
        "The recommended mode preserves real eye movement, body mechanics and object interaction from a consenting performer."
    )

    with st.form("reality_project_setup"):
        a, b = st.columns(2)
        with a:
            character_name = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA.keys()))
            topic = st.text_input(
                "Video topic or episode",
                placeholder="Sofia corrects one eyeliner mistake",
            )
            workflow_mode = st.selectbox(
                "Workflow",
                [
                    "Actor performance + fictional identity transfer",
                    "Fully synthetic reference-controlled shots",
                ],
            )
            target_language = st.selectbox("Language", ["Italian", "English", "Albanian", "Macedonian"])
            platform = st.selectbox("Platform", ["TikTok + YouTube Shorts", "TikTok", "YouTube Shorts"])
        with b:
            actor_consent = st.checkbox("Consenting actor/performance rights confirmed")
            face_rights = st.checkbox("The digital face is fictional or fully authorized")
            voice_rights = st.checkbox("The voice is licensed, synthetic, or used with consent")
            media_rights = st.checkbox("Property, product and background media rights are confirmed")
            ai_disclosure = st.checkbox("Prepare AI-generated-content disclosure", value=True)
            rights_notes = st.text_area("Rights/consent notes", placeholder="Actor agreement, voice license, source media permissions...")
        create_project = st.form_submit_button("Create realism project", type="primary")

    if create_project:
        if not topic.strip():
            st.error("Enter a topic or episode.")
        else:
            character = load_character(character_name)
            rights = RightsRecord(
                actor_consent=actor_consent,
                face_identity_is_fictional_or_authorized=face_rights,
                voice_is_licensed_or_consented=voice_rights,
                property_and_product_media_authorized=media_rights,
                ai_disclosure_required=ai_disclosure,
                notes=rights_notes.strip(),
            )
            new_project = RealismProject(
                project_id=safe_project_id(character_name, topic),
                character_name=character_name,
                topic=topic.strip(),
                workflow_mode=workflow_mode,
                target_language=target_language,
                platform=platform,
                created_at=utc_now_iso(),
                rights=rights,
                shots=default_shot_plan(character, topic.strip()),
                status="PLANNING",
            )
            save_project(new_project)
            st.session_state.reality_project = new_project
            project = new_project
            st.success(f"Created project: {new_project.project_id}")

    if project is not None:
        st.markdown("### Current project")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Character", project.character_name)
        p2.metric("Shots", len(project.shots))
        p3.metric("Planned duration", f"{project.total_duration_seconds:.1f} sec")
        p4.metric("Status", project.status)

        blockers = project.rights.hard_blockers()
        if blockers:
            st.error("Production is blocked until rights are confirmed:\n\n" + "\n".join(f"• {item}" for item in blockers))
        else:
            st.success("Rights and consent gate passed for production planning.")

        st.code(
            "Consenting performance → identity transfer → licensed voice/lip sync → sound design → shot QA → vertical MP4",
            language=None,
        )

with assets_tab:
    if project is None:
        st.info("Create or open a project first.")
    else:
        st.subheader("Capture the human detail that makes the character believable")
        st.caption(
            "Upload short performance footage with natural blinking, breathing, eye-line changes and real object interaction. Raw assets stay local under storage/ and are ignored by Git."
        )

        project_paths = ensure_project_structure(project.project_id)

        left, right = st.columns(2)
        with left:
            performance_file = st.file_uploader(
                "Consenting actor performance video",
                type=["mp4", "mov", "webm", "m4v"],
                key=f"performance_{project.project_id}",
            )
            performance_confirm = st.checkbox(
                "I confirm the performer consented to this use.",
                key=f"performance_rights_{project.project_id}",
            )
            if performance_file is not None:
                st.video(performance_file)
                if st.button("Save performance footage", type="primary"):
                    if not performance_confirm:
                        st.error("Confirm performer consent first.")
                    else:
                        try:
                            path = save_project_asset(
                                project.project_id,
                                "performance_video",
                                performance_file.name,
                                performance_file.getvalue(),
                            )
                            st.success(f"Saved: {path}")
                        except ValueError as error:
                            st.error(str(error))

            identity_file = st.file_uploader(
                "Approved master identity image",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"identity_{project.project_id}",
            )
            identity_confirm = st.checkbox(
                "This face is fictional or I have authorization to use it.",
                key=f"identity_rights_{project.project_id}",
            )
            if identity_file is not None:
                st.image(identity_file, width=320)
                if st.button("Save master identity image"):
                    if not identity_confirm:
                        st.error("Confirm identity authorization first.")
                    else:
                        try:
                            path = save_project_asset(
                                project.project_id,
                                "identity_image",
                                identity_file.name,
                                identity_file.getvalue(),
                            )
                            st.success(f"Saved: {path}")
                        except ValueError as error:
                            st.error(str(error))

        with right:
            voice_file = st.file_uploader(
                "Licensed voice reference",
                type=["mp3", "wav", "m4a", "aac", "flac"],
                key=f"voice_{project.project_id}",
            )
            voice_confirm = st.checkbox(
                "I confirm this voice is licensed, synthetic, or recorded with consent.",
                key=f"voice_rights_{project.project_id}",
            )
            if voice_file is not None:
                st.audio(voice_file)
                if st.button("Save voice reference"):
                    if not voice_confirm:
                        st.error("Confirm voice rights first.")
                    else:
                        try:
                            path = save_project_asset(
                                project.project_id,
                                "voice_sample",
                                voice_file.name,
                                voice_file.getvalue(),
                            )
                            st.success(f"Saved: {path}")
                        except ValueError as error:
                            st.error(str(error))

            st.markdown("#### Performance capture instructions")
            st.markdown(
                """
                - Record in stable, soft light without beauty filters.
                - Capture real object interaction instead of generic hand gestures.
                - Let the actor react before speaking.
                - Include natural pauses, breathing and brief eye-line changes.
                - Record each planned shot separately, ideally 3–8 seconds.
                - Keep the camera, lighting and wardrobe stable within a scene.
                """
            )

        st.markdown("### Local project folders")
        st.json({name: str(path) for name, path in project_paths.items()})

with shots_tab:
    if project is None:
        st.info("Create or open a project first.")
    else:
        character: CharacterDNA = load_character(project.character_name)
        st.subheader("Direct short, controllable shots")
        st.caption("Long one-prompt videos drift. This editor keeps each shot short enough to regenerate individually.")

        action_names = [item["name"] for item in character.actions]
        location_names = [item["name"] for item in character.locations]
        wardrobe_names = [item["name"] for item in character.wardrobe]
        emotion_names = character.voice.emotional_range

        edited_shots: list[ShotSpec] = []
        with st.form(f"shot_editor_{project.project_id}"):
            for shot in project.shots:
                with st.expander(f"Shot {shot.shot_number}: {shot.title}", expanded=shot.shot_number == 1):
                    c1, c2 = st.columns(2)
                    with c1:
                        title = st.text_input("Shot title", value=shot.title, key=f"title_{project.project_id}_{shot.shot_number}")
                        duration = st.slider("Duration", 2.0, 10.0, float(shot.duration_seconds), 0.5, key=f"duration_{project.project_id}_{shot.shot_number}")
                        dialogue = st.text_area("Dialogue", value=shot.dialogue, key=f"dialogue_{project.project_id}_{shot.shot_number}")
                        emotion = st.selectbox(
                            "Emotion",
                            emotion_names,
                            index=emotion_names.index(shot.emotion) if shot.emotion in emotion_names else 0,
                            key=f"emotion_{project.project_id}_{shot.shot_number}",
                        )
                    with c2:
                        action = st.selectbox(
                            "Physical action",
                            action_names,
                            index=action_names.index(shot.action_name) if shot.action_name in action_names else 0,
                            key=f"action_{project.project_id}_{shot.shot_number}",
                        )
                        location = st.selectbox(
                            "Location",
                            location_names,
                            index=location_names.index(shot.location_name) if shot.location_name in location_names else 0,
                            key=f"location_{project.project_id}_{shot.shot_number}",
                        )
                        wardrobe = st.selectbox(
                            "Wardrobe",
                            wardrobe_names,
                            index=wardrobe_names.index(shot.wardrobe_name) if shot.wardrobe_name in wardrobe_names else 0,
                            key=f"wardrobe_{project.project_id}_{shot.shot_number}",
                        )
                        camera = st.text_area("Camera direction", value=shot.camera, key=f"camera_{project.project_id}_{shot.shot_number}")
                        notes = st.text_area("Performance/editing notes", value=shot.notes, key=f"notes_{project.project_id}_{shot.shot_number}")
                    edited_shots.append(
                        ShotSpec(
                            shot_number=shot.shot_number,
                            title=title.strip(),
                            duration_seconds=float(duration),
                            dialogue=dialogue.strip(),
                            emotion=emotion,
                            action_name=action,
                            location_name=location,
                            wardrobe_name=wardrobe,
                            camera=camera.strip(),
                            performance_source=shot.performance_source,
                            notes=notes.strip(),
                        )
                    )
            save_shots = st.form_submit_button("Save directed shots", type="primary")

        if save_shots:
            updated = deepcopy(project)
            updated.shots = edited_shots
            updated.status = "DIRECTED"
            save_project(updated)
            st.session_state.reality_project = updated
            project = updated
            st.success("Shot plan saved.")

        st.markdown("### Timing")
        st.code(generate_srt(project.shots), language=None)

with package_tab:
    if project is None:
        st.info("Create or open a project first.")
    else:
        character = load_character(project.character_name)
        st.subheader("Generate the provider-neutral production package")
        st.caption(
            "The package contains identity DNA, visual prompts, actor directions, voice directions, negative prompts, continuity checks and subtitles."
        )

        manifest = build_realism_manifest(project, character)
        blockers = manifest["rights_status"]["hard_blockers"]
        if blockers:
            st.error("Package may be inspected, but production is blocked:\n\n" + "\n".join(f"• {item}" for item in blockers))

        st.markdown("### Production stages")
        stage_columns = st.columns(5)
        for column, stage in zip(stage_columns, manifest["stages"]):
            with column:
                st.markdown(
                    f"""
                    <div class="pipeline-card">
                      <b>{stage['stage']}. {stage['name']}</b><br><br>
                      <small>{stage['output']}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("### Shot handoff")
        shot_rows = [
            {
                "Shot": shot["shot_number"],
                "Title": shot["title"],
                "Duration": shot["duration_seconds"],
                "Emotion": shot["emotion"],
                "Action": shot["action"]["name"],
                "Location": shot["location"]["name"],
            }
            for shot in manifest["shots"]
        ]
        st.dataframe(shot_rows, use_container_width=True, hide_index=True)

        selected_shot = st.selectbox(
            "Inspect shot package",
            [shot["shot_number"] for shot in manifest["shots"]],
            format_func=lambda value: f"Shot {value}",
        )
        current_shot = next(shot for shot in manifest["shots"] if shot["shot_number"] == selected_shot)
        st.text_area("Visual identity prompt", current_shot["visual_prompt"], height=220)
        st.text_area("Performance direction", current_shot["performance_direction"], height=150)
        st.text_area("Voice direction", current_shot["voice_direction"], height=140)
        st.text_area("Negative prompt", current_shot["negative_prompt"], height=100)

        if st.button("Build production ZIP", type="primary"):
            archive = export_project_package(project, character)
            st.session_state[f"production_zip_{project.project_id}"] = str(archive)
            st.success(f"Created: {archive}")

        archive_value = st.session_state.get(f"production_zip_{project.project_id}")
        if archive_value and Path(archive_value).exists():
            archive_path = Path(archive_value)
            st.download_button(
                "Download production package",
                data=archive_path.read_bytes(),
                file_name=archive_path.name,
                mime="application/zip",
            )

with assembly_tab:
    if project is None:
        st.info("Create or open a project first.")
    else:
        st.subheader("Upload approved generated shots and assemble the master video")
        st.caption(
            "Generate or identity-transfer each shot using your chosen authorized provider, approve it, then upload the final shot clips here in numerical order."
        )

        selected_number = st.selectbox(
            "Shot number",
            [shot.shot_number for shot in project.shots],
            format_func=lambda number: f"Shot {number:02d}",
        )
        generated_clip = st.file_uploader(
            "Approved shot clip",
            type=["mp4", "mov", "webm", "m4v"],
            key=f"generated_clip_{project.project_id}_{selected_number}",
        )
        if generated_clip is not None:
            st.video(generated_clip)
            if st.button("Save approved shot clip", type="primary"):
                try:
                    path = save_project_asset(
                        project.project_id,
                        "generated_shot",
                        generated_clip.name,
                        generated_clip.getvalue(),
                        shot_number=int(selected_number),
                    )
                    st.success(f"Saved: {path}")
                except ValueError as error:
                    st.error(str(error))

        narration = st.file_uploader(
            "Optional final licensed narration/audio mix",
            type=["mp3", "wav", "m4a", "aac", "flac"],
            key=f"narration_{project.project_id}",
        )
        if narration is not None and st.button("Save narration mix"):
            try:
                path = save_project_asset(
                    project.project_id,
                    "narration_audio",
                    narration.name,
                    narration.getvalue(),
                )
                st.session_state[f"narration_path_{project.project_id}"] = str(path)
                st.success(f"Saved: {path}")
            except ValueError as error:
                st.error(str(error))

        shot_files = ordered_generated_shots(project.project_id)
        st.markdown("### Approved shot clips")
        if shot_files:
            st.dataframe(
                [{"Order": index + 1, "File": path.name, "Path": str(path)} for index, path in enumerate(shot_files)],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No approved shot clips saved yet.")

        character = load_character(project.character_name)
        saved = save_manifest_and_subtitles(project, character)
        narration_path_value = st.session_state.get(f"narration_path_{project.project_id}")
        narration_path = Path(narration_path_value) if narration_path_value else None

        ffmpeg = find_ffmpeg()
        if ffmpeg:
            st.success(f"FFmpeg found: {ffmpeg}")
        else:
            st.error("FFmpeg is not installed or is not available on PATH. Rendering cannot start.")

        use_subtitles = st.checkbox("Burn subtitles into the final video", value=True)
        if st.button("Render 1080 × 1920 MP4", type="primary", disabled=not bool(ffmpeg)):
            try:
                output_path = ensure_project_structure(project.project_id)["exports"] / f"{project.project_id}-master.mp4"
                rendered = render_vertical_video(
                    shot_files,
                    output_path,
                    narration_audio=narration_path,
                    subtitles_srt=saved["subtitles"] if use_subtitles else None,
                    ffmpeg_binary=ffmpeg,
                )
                updated = deepcopy(project)
                updated.status = "RENDERED"
                save_project(updated)
                st.session_state.reality_project = updated
                project = updated
                st.session_state[f"rendered_path_{project.project_id}"] = str(rendered)
                st.success(f"Rendered: {rendered}")
            except (ValueError, RuntimeError) as error:
                st.error(str(error))
            except Exception as error:
                st.error(f"FFmpeg rendering failed: {error}")

        rendered_value = st.session_state.get(f"rendered_path_{project.project_id}")
        if rendered_value and Path(rendered_value).exists():
            rendered_path = Path(rendered_value)
            st.video(str(rendered_path))
            st.download_button(
                "Download master MP4",
                data=rendered_path.read_bytes(),
                file_name=rendered_path.name,
                mime="video/mp4",
            )

with qa_tab:
    if project is None:
        st.info("Create or open a project first.")
    else:
        st.subheader("Reality Gate")
        st.caption("A failed shot is regenerated individually. Do not hide broken anatomy, identity drift or rights problems inside a fast edit.")

        check_descriptions = {
            "face_identity": "Face geometry matches the approved master and angle references.",
            "skin": "Skin retains realistic texture; no plastic beauty-filter appearance.",
            "eyes_hair": "Eye color, hair and signature item remain stable.",
            "micro_expression": "Reaction begins before dialogue; blinking, breathing and eye-line changes feel natural.",
            "hands_objects": "Hands, tools, doors, phones and products interact believably.",
            "lip_sync": "Mouth shape, timing and emotion match the licensed voice.",
            "body_motion": "Walking, weight shift and posture follow real human mechanics.",
            "lighting": "Light direction, shadows and skin tone match the environment.",
            "world_continuity": "Room geography, objects, wardrobe and story facts remain stable.",
            "audio": "Room tone, footsteps, object sounds and breathing support the image.",
            "captions_facts": "Captions, spoken numbers and verified facts match.",
            "disclosure": "Required AI disclosure is prepared.",
        }

        qa_values: dict[str, bool] = {}
        for key, description in check_descriptions.items():
            qa_values[key] = st.checkbox(description, key=f"reality_qa_{project.project_id}_{key}")

        result = evaluate_realism_gate(qa_values, project.rights)
        q1, q2, q3 = st.columns(3)
        q1.metric("Reality score", f"{result['score']}%")
        q2.metric("Passed", f"{result['passed']}/{result['total']}")
        q3.metric("Decision", result["status"])

        if result["hard_blockers"]:
            st.error("\n".join(f"• {item}" for item in result["hard_blockers"]))
        elif result["failed_checks"]:
            st.warning("Fix or regenerate:\n\n" + "\n".join(f"• {item}" for item in result["failed_checks"]))
        else:
            st.success("All automated checklist items passed. A human must still watch the entire video before publishing.")

        qa_report = {
            "project_id": project.project_id,
            "character": project.character_name,
            "result": result,
            "checks": qa_values,
            "rights": project.rights.__dict__,
        }
        st.download_button(
            "Download QA report",
            data=json.dumps(qa_report, ensure_ascii=False, indent=2),
            file_name=f"{project.project_id}-qa-report.json",
            mime="application/json",
        )
