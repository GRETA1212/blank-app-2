from __future__ import annotations

from datetime import date

import streamlit as st

from creator_os import calendar_range, load_data, record_income, revenue_summary
from creator_studio import SEED_CHARACTERS


st.set_page_config(page_title="Calendar & Revenue", page_icon="💶", layout="wide")
st.title("💶 Content Calendar & Revenue")
st.caption("See what is planned, what is in production, what was published, and which income sources are actually working.")

data = load_data()
calendar_tab, revenue_tab = st.tabs(["Content Calendar", "Revenue"])

with calendar_tab:
    start = st.date_input("Calendar starts", date.today())
    days = st.slider("Days", 7, 90, 30)
    items = calendar_range(data, start, days)
    if not items:
        st.info("Approve ideas in Daily Planner to create calendar entries.")
    else:
        st.dataframe(
            [
                {
                    "Date": item.get("date"),
                    "Creator": item.get("character"),
                    "Video": item.get("title"),
                    "Platform": item.get("platform"),
                    "Status": item.get("status"),
                    "Video ID": item.get("video_id") or "",
                    "Project": item.get("project_id") or "",
                }
                for item in items
            ],
            use_container_width=True,
            hide_index=True,
        )

with revenue_tab:
    summary = revenue_summary(data)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total recorded income", f"€{summary['total_eur']:,.2f}")
    c2.metric("Income sources", len(summary["by_source"]))
    c3.metric("Creators earning", len(summary["by_character"]))

    left, right = st.columns(2)
    with left:
        st.markdown("### By source")
        st.dataframe(
            [{"Source": key, "Amount (€)": value} for key, value in summary["by_source"].items()],
            use_container_width=True,
            hide_index=True,
        )
    with right:
        st.markdown("### By creator")
        st.dataframe(
            [{"Creator": key, "Amount (€)": value} for key, value in summary["by_character"].items()],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Record income")
    with st.form("creator_os_income"):
        character = st.selectbox("Creator", list(SEED_CHARACTERS))
        source = st.selectbox(
            "Source",
            ["YouTube", "TikTok", "Affiliate", "Sponsor", "Digital product", "Property lead", "Client service", "Licensing"],
        )
        amount = st.number_input("Amount (€)", min_value=0.0, value=0.0)
        occurred_on = st.date_input("Date", date.today(), key="income_date")
        video_id = st.text_input("Related video ID (optional)")
        note = st.text_input("Note")
        save = st.form_submit_button("Record income", type="primary")
    if save and amount > 0:
        record_income(
            data,
            character=character,
            source=source,
            amount_eur=amount,
            occurred_on=occurred_on,
            video_id=video_id.strip() or None,
            note=note,
        )
        st.success("Income recorded.")
        st.rerun()

    if data["income"]:
        st.markdown("### Income history")
        st.dataframe(data["income"], use_container_width=True, hide_index=True)
