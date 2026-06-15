import streamlit as st
from supabase import create_client, Client

@st.cache_resource(show_spinner=False)
def get_db() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

db = get_db()
