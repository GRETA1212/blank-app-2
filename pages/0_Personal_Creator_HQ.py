import streamlit as st

st.set_page_config(page_title="Greta Creator HQ", page_icon="👑", layout="wide")
st.title("👑 Greta Creator HQ")
st.info("The connected workflow now lives in Greta Private Studio.")
if st.button("Open Greta Private Studio", type="primary"):
    st.switch_page("pages/0_Private_Studio.py")
