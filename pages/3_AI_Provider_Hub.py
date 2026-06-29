from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from generation_orchestrator import (
    build_generation_plan,
    generate_all_voices,
    generate_shot_voice,
    load_provider_jobs,
    provider_readiness,
    refresh_all_jobs,
    refresh_shot_job,
    save_all_completed,
    save_completed_video,
    submit_all_shots,
    submit_shot_job,
)
from object_storage import ObjectStorage
from providers import ProviderError
from realism_pipeline import list_projects, load_project


st.set_page_config(page_title="AI Provider Hub", page_icon="🔌", layout="wide")
st.title("🔌 AI Provider Hub")
st.caption("Generate all planned shots, monitor provider jobs, and return finished clips to Reality Pipeline.")

SECRET_NAMES = [
    "HEYGEN_API_KEY",
    "HEYGEN_AVATAR_ID",
    "HEYGEN_VOICE_ID",
    "HEYGEN_ENGINE",
    "RUNWAYML_API_SECRET",
    "RUNWAY_MODEL",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ELEVENLABS_MODEL_ID",
    "OBJECT_STORAGE_BUCKET",
    "OBJECT_STORAGE_REGION",
    "OBJECT_STORAGE_ENDPOINT_URL",
    "OBJECT_STORAGE_ACCESS_KEY_ID",
    "OBJECT_STORAGE_SECRET_ACCESS_KEY",
    "OBJECT_STORAGE_PUBLIC_BASE_URL",
    "OBJECT_STORAGE_PREFIX",
]
for name in SECRET_NAMES:
    try:
        if not os.getenv(name) and name in st.secrets:
            os.environ[name] = str(st.secrets[name])
    except FileNotFoundError:
        pass

projects = list_projects()
if not projects:
    st.warning("Create a project in Reality Pipeline first.")
    st.stop()

project_id = st.selectbox(
    "Project",
    [item["project_id"] for item in projects],
    format_func=lambda value: next(
        f"{item['character_name']} — {item['topic']} ({item['status']})"
        for item in projects
        if item["project_id"] == value
    ),
)
project = load_project(project_id)
blockers = project.rights.hard_blockers()

readiness = provider_readiness()
st.subheader("Readiness")
rows = [
    {
        "Service": item["provider"],
        "Role": item["role"],
        "Ready": "Yes" if item["configured"] else "No",
        "Missing": ", ".join(item["missing"]),
    }
    for item in readiness
]
rows.append(
    {
        "Service": "Object storage",
        "Role": "Temporary HTTPS media links",
        "Ready": "Yes" if ObjectStorage().configured else "No",
        "Missing": "" if ObjectStorage().configured else "Storage credentials",
    }
)
st.dataframe(rows, use_container_width=True, hide_index=True)

if blockers:
    st.error("Generation is blocked until all rights confirmations are complete.")
    for blocker in blockers:
        st.write(f"• {blocker}")
    st.stop()

plan_key = f"provider_plan_{project_id}"
plan_path = Path("storage") / "realism_projects" / project_id / "manifests" / "provider_generation_plan.json"
if st.button("Build generation plan", type="primary"):
    try:
        st.session_state[plan_key] = build_generation_plan(project)
        st.rerun()
    except ProviderError as error:
        st.error(str(error))

plan = st.session_state.get(plan_key)
if plan is None and plan_path.exists():
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        plan = None

if plan is None:
    st.info("Build the generation plan first.")
    st.stop()

st.metric("Estimated first-pass cost", f"€{float(plan.get('estimated_total_cost_eur', 0)):,.2f}")
st.dataframe(
    [
        {
            "Shot": item["shot_number"],
            "Title": item["title"],
            "Provider": item["provider"],
            "Seconds": item["duration_seconds"],
            "Estimated cost (€)": item.get("estimated_cost_eur"),
        }
        for item in plan["shots"]
    ],
    use_container_width=True,
    hide_index=True,
)

st.subheader("One-click workflow")
reference_url = st.text_input(
    "Optional approved reference image URL",
    help="Leave empty to upload the local project reference through configured object storage.",
)
start_col, refresh_col, save_col, voice_col = st.columns(4)
with start_col:
    if st.button("Generate all shots", type="primary", use_container_width=True):
        try:
            result = submit_all_shots(
                project_id,
                reference_image_url=reference_url.strip() or None,
                publish_local_reference=not bool(reference_url.strip()),
            )
            st.json(result)
            st.rerun()
        except ProviderError as error:
            st.error(str(error))
with refresh_col:
    if st.button("Refresh all jobs", use_container_width=True):
        st.json(refresh_all_jobs(project_id))
        st.rerun()
with save_col:
    if st.button("Save finished clips", use_container_width=True):
        st.json(save_all_completed(project_id))
with voice_col:
    if st.button("Generate all voices", use_container_width=True):
        st.json(generate_all_voices(project_id))

st.subheader("Individual shot")
shot_numbers = [int(item["shot_number"]) for item in plan["shots"]]
selected_shot = st.selectbox("Shot", shot_numbers, format_func=lambda value: f"Shot {value:02d}")
shot_plan = next(item for item in plan["shots"] if int(item["shot_number"]) == selected_shot)
provider_name = st.selectbox("Provider", ["heygen", "runway"], index=0 if shot_plan["provider"] == "heygen" else 1)
single_reference = st.text_input("Reference URL for this shot", key="single_reference") if provider_name == "runway" else ""
submit_col, shot_voice_col = st.columns(2)
with submit_col:
    if st.button("Submit selected shot", use_container_width=True):
        try:
            st.json(
                submit_shot_job(
                    project_id,
                    selected_shot,
                    provider_name,
                    reference_image_url=single_reference.strip() or None,
                )
            )
            st.rerun()
        except ProviderError as error:
            st.error(str(error))
with shot_voice_col:
    if st.button("Generate selected voice", use_container_width=True):
        try:
            output = generate_shot_voice(project_id, selected_shot)
            st.audio(str(output))
        except ProviderError as error:
            st.error(str(error))

st.subheader("Provider jobs")
jobs = load_provider_jobs(project_id)
if not jobs:
    st.info("No jobs yet.")
    st.stop()

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
selected_job_id = st.selectbox("Job", [item["id"] for item in jobs])
selected_job = next(item for item in jobs if item["id"] == selected_job_id)
job_refresh_col, job_save_col = st.columns(2)
with job_refresh_col:
    if st.button("Refresh selected job", use_container_width=True):
        try:
            st.json(
                refresh_shot_job(
                    project_id,
                    selected_job["provider"],
                    selected_job["provider_job_id"],
                    int(selected_job["shot_number"]),
                )
            )
            st.rerun()
        except ProviderError as error:
            st.error(str(error))
with job_save_col:
    can_save = selected_job.get("status") == "SUCCEEDED" and bool(selected_job.get("output_url"))
    if st.button("Save selected clip", disabled=not can_save, use_container_width=True):
        try:
            st.success(str(save_completed_video(project_id, selected_job_id)))
        except ProviderError as error:
            st.error(str(error))
