from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st

from character_lab import DEFAULT_CHARACTER_DNA

st.set_page_config(page_title="Greta Creator HQ", page_icon="👑", layout="wide")

DATA_FILE = Path("storage/personal_creator_hq.json")
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"monthly_goal": 1000, "accounts": [], "videos": [], "income": []}


def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


data = load_data()

st.title("👑 Greta Creator HQ")
st.caption("Your private studio for managing virtual creators, videos and income.")
st.success("Personal mode: one owner, local storage, manual approval and manual publishing.")

goal = st.number_input("Monthly income goal (€)", min_value=0, value=int(data["monthly_goal"]), step=100)
if goal != data["monthly_goal"]:
    data["monthly_goal"] = int(goal)
    save_data(data)

month_key = date.today().strftime("%Y-%m")
month_income = sum(float(x["amount_eur"]) for x in data["income"] if x["date"].startswith(month_key))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Creator accounts", len(data["accounts"]))
c2.metric("Videos planned", len(data["videos"]))
c3.metric("Videos published", sum(1 for x in data["videos"] if x["status"] == "Published"))
c4.metric("Income this month", f"€{month_income:,.2f}")
st.progress(min(month_income / goal, 1.0) if goal else 0.0, text=f"€{month_income:,.2f} of €{goal:,.2f}")

accounts_tab, videos_tab, income_tab, routine_tab = st.tabs(["Creator Accounts", "Video Queue", "Income", "Daily Routine"])

with accounts_tab:
    st.subheader("Your creator accounts")
    if data["accounts"]:
        st.dataframe(data["accounts"], use_container_width=True, hide_index=True)
    else:
        st.info("Start by adding Sofia, Elena and Luna.")

    with st.form("account_form"):
        character = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA.keys()))
        platform = st.selectbox("Platform", ["TikTok", "YouTube", "Instagram", "Facebook"])
        handle = st.text_input("Account handle")
        income_route = st.selectbox("Main income route", ["Platform income", "Affiliate", "Sponsor", "Property lead", "Client service", "Membership"])
        status = st.selectbox("Status", ["Planning", "Active", "Paused"])
        submitted = st.form_submit_button("Add account", type="primary")
    if submitted:
        if not handle.strip():
            st.error("Enter the account handle.")
        else:
            data["accounts"].append({"character": character, "platform": platform, "handle": handle.strip(), "income_route": income_route, "status": status})
            save_data(data)
            st.rerun()

with videos_tab:
    st.subheader("Content production queue")
    if data["videos"]:
        st.dataframe(data["videos"], use_container_width=True, hide_index=True)
    else:
        st.info("No videos planned yet.")

    with st.form("video_form"):
        character = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA.keys()), key="video_character")
        title = st.text_input("Video idea")
        platform = st.selectbox("Platform", ["TikTok", "YouTube Shorts", "Instagram Reels", "All short-form"], key="video_platform")
        status = st.selectbox("Status", ["Idea", "Scripted", "Producing", "Ready", "Published", "Paused"])
        planned_date = st.date_input("Planned date", value=date.today())
        objective = st.selectbox("Objective", ["Views", "Followers", "Affiliate click", "Sponsor portfolio", "Property lead", "Client inquiry"])
        submitted = st.form_submit_button("Add video", type="primary")
    if submitted:
        if not title.strip():
            st.error("Enter the video idea.")
        else:
            data["videos"].append({"character": character, "title": title.strip(), "platform": platform, "status": status, "planned_date": planned_date.isoformat(), "objective": objective})
            save_data(data)
            st.rerun()

with income_tab:
    st.subheader("Income tracker")
    if data["income"]:
        st.dataframe(data["income"], use_container_width=True, hide_index=True)
    else:
        st.info("No income recorded yet.")

    with st.form("income_form"):
        character = st.selectbox("Character", list(DEFAULT_CHARACTER_DNA.keys()), key="income_character")
        source = st.selectbox("Source", ["TikTok", "YouTube", "Affiliate", "Sponsor", "Property lead", "Client service", "Membership"])
        amount = st.number_input("Amount (€)", min_value=0.0, value=0.0, step=10.0)
        received_date = st.date_input("Date", value=date.today(), key="income_date")
        note = st.text_input("Related video or note")
        submitted = st.form_submit_button("Record income", type="primary")
    if submitted:
        if amount <= 0:
            st.error("Enter an amount greater than zero.")
        else:
            data["income"].append({"character": character, "source": source, "amount_eur": float(amount), "date": received_date.isoformat(), "note": note.strip()})
            save_data(data)
            st.rerun()

with routine_tab:
    st.subheader("How you operate the studio")
    st.markdown(
        """
        **Every morning**
        1. Check yesterday's views, retention, followers and income.
        2. Choose one proven creator format for today.
        3. Keep only one experimental video in the daily plan.

        **Production**
        1. Use Character Lab to preserve the face and voice.
        2. Use Reality Pipeline to direct and assemble the video.
        3. Move the video to Ready only after quality review.

        **Publishing**
        1. Post manually to the correct account.
        2. Apply required AI-content disclosure.
        3. Record the result after 72 hours.

        **Weekly decision**
        - 70% of your time goes to proven winners.
        - 20% goes to improving promising formats.
        - 10% goes to new experiments.
        """
    )
