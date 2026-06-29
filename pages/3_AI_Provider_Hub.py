from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from generation_orchestrator import (
    build_generation_plan,
    generate_shot_voice,
    load_provider_jobs,
    provider_readiness,
    refresh_shot_job,
    save_completed_video,
    submit_shot_job,
)
from providers import ProviderError
from realism_pipeline import list_projects, load_project


st.set_page_config(page_title="AI Provider Hub", page_icon="🔌", layout="wide")

st.title("🔌 AI Provider Hub")
st.caption("Connect the rights-approved Reality Pipeline to current generation providers without exposing API keys in the browser.")
st.info("Use fictional or fully authorized identities and licensed or consented voices only. The Reality Pipeline rights gate is enforced before any provider request.")

# Streamlit Cloud/local secrets can supply the same names as .env without exposing them in the page.
for secret_name in [
    "HEYGEN_API_KEY",
    "HEYGEN_AVATAR_ID",
    "HEYGEN_VOICE_ID",
    "RUNWAYML_API_SECRET",
    "RUNWAY_MODEL",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ELEVENLABS_MODEL_ID",
]:
    try:
        if not os.getenv(secret_name) and secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
    except FileNotFoundError:
        pass

projects = list_projects()
if not projects:
    st.warning("Create a project in Reality Pipeline first.")
    st.stop()

project_id = st.selectbox(
    "Reality Pipeline project",
    [item["project_id"] for item in projects],
    format_func=lambda value: next(
        f"{item['character_name']} — {item['topic']} ({item['status']})"
        for item in projects
        if item["project_id"] == value
    ),
)
project = load_project(project_id)
blockers = project.rights.hard_blockers()

st.subheader("Provider readiness")
readiness = provider_readiness()
st.dataframe(
    [
        {
            "Provider": item["provider"],
            "Role": item["role"],
            "Ready": "Yes" if item["configured"] else "No",
            "Missing configuration": ", ".join(item["missing"]),
        }
        for item in readiness
    ],
    use_container_width=True,
    hide_index=True,
)
st.caption("Keys are read only from environment variables or Streamlit secrets; they are never stored in project JSON or shown in this page.")

if blockers:
    st.error("Provider generation is blocked until these rights are confirmed:\n\n" + "\n".join(f"• {item}" for item in blockers))
    st.stop()

plan_key = f"provider_plan_{project_id}"
if st.button("Build provider generation plan", type="primary"):
    try:
        st.session_state[plan_key] = build_generation_plan(project)
        st.success("Provider plan created from the approved Character DNA and shot directions.")
    except ProviderError as error:
        st.error(str(error))

plan = st.session_state.get(plan_key)
plan_path = Path("storage") / "realism_projects" / project_id / "manifests" / "provider_generation_plan.json"
if plan is None and plan_path.exists():
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        st.session_state[plan_key] = plan
    except json.JSONDecodeError:
        plan = None

if plan is None:
    st.info("Build the provider generation plan to route talking shots to HeyGen and lifestyle shots to Runway.")
    st.stop()

st.subheader("Shot routing")
st.dataframe(
    [
        {
            "Shot": item["shot_number"],
            "Title": item["title"],
            "Provider": item["provider"],
            "Purpose": item["purpose"],
            "Duration": item["duration_seconds"],
            "Reference URL needed": item["requires_reference_image_url"],
        }
        for item in plan["shots"]
    ],
    use_container_width=True,
    hide_index=True,
)
st.download_button(
    "Download provider plan",
    data=json.dumps(plan, ensure_ascii=False, indent=2),
    file_name=f"{project_id}-provider-plan.json",
    mime="application/json",
)

shot_numbers = [int(item["shot_number"]) for item in plan["shots"]]
selected_shot = st.selectbox("Shot", shot_numbers, format_func=lambda value: f"Shot {value:02d}")
shot_plan = next(item for item in plan["shots"] if int(item["shot_number"]) == selected_shot)
provider_name = st.selectbox(
    "Video provider",
    ["heygen", "runway"],
    index=0 if shot_plan["provider"] == "heygen" else 1,
)

reference_url = ""
if provider_name == "runway":
    reference_url = st.text_input(
        "Approved Sofia reference-image HTTPS URL",
        placeholder="https://your-storage.example/sofia-master.jpg",
        help="The first version uses a secure public/signed URL. Direct object-storage uploads come next.",
    )

left, right = st.columns(2)
with left:
    if st.button("Submit selected shot", type="primary"):
        try:
            record = submit_shot_job(
                project_id,
                selected_shot,
                provider_name,
                reference_image_url=reference_url.strip() or None,
            )
            st.success(f"Submitted {record['provider']} job {record['provider_job_id']}.")
            st.rerun()
        except ProviderError as error:
            st.error(str(error))
with right:
    if st.button("Generate licensed voice for selected shot"):
        try:
            output = generate_shot_voice(project_id, selected_shot)
            st.success(f"Saved voice: {output}")
            st.audio(str(output))
        except ProviderError as error:
            st.error(str(error))

st.subheader("Generation jobs")
jobs = load_provider_jobs(project_id)
if not jobs:
    st.info("No provider jobs have been submitted for this project.")
else:
    st.dataframe(
        [
            {
                "ID": item["id"],
                "Shot": item["shot_number"],
                "Provider": item["provider"],
                "Status": item["status"],
                "Error": item.get("error") or "",
                "Updated": item.get("updated_at", ""),
            }
            for item in jobs
        ],
        use_container_width=True,
        hide_index=True,
    )
    selected_job_id = st.selectbox("Job to manage", [item["id"] for item in jobs])
    selected_job = next(item for item in jobs if item["id"] == selected_job_id)
    manage_left, manage_right = st.columns(2)
    with manage_left:
        if st.button("Refresh job status"):
            try:
                refreshed = refresh_shot_job(
                    project_id,
                    selected_job["provider"],
                    selected_job["provider_job_id"],
                    int(selected_job["shot_number"]),
                )
                st.success(f"Status: {refreshed['status']}")
                st.rerun()
            except ProviderError as error:
                st.error(str(error))
    with manage_right:
        can_save = selected_job.get("status") == "SUCCEEDED" and bool(selected_job.get("output_url"))
        if st.button("Save completed clip into Reality Pipeline", disabled=not can_save):
            try:
                saved = save_completed_video(project_id, selected_job_id)
                st.success(f"Saved: {saved}. It is now available in Assemble MP4.")
            except ProviderError as error:
                st.error(str(error))
