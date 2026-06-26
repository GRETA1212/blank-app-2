import streamlit as st

st.set_page_config(page_title="Greta Creator HQ", page_icon="👑", layout="wide")
st.title("👑 Greta Creator HQ")
st.info("This page has moved to the connected Studio Control Center.")
if st.button("Open Studio Control Center", type="primary"):
    st.switch_page("pages/0_Studio_Control_Center.py")
