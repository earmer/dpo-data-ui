import streamlit as st

def init_session_state():
    if 'current_dataset' not in st.session_state:
        st.session_state.current_dataset = None
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None

def set_page_config():
    st.set_page_config(
        page_title="DPO Data Generation",
        layout="wide"
    )