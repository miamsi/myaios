import streamlit as st
from services.supabase_client import db

if "user_id" not in st.session_state:
    st.warning("Secure session missing. Redirecting to main login...")
    st.switch_page("app.py")
    st.stop()

st.title("Semantic Memory")
st.write("This is what the OS remembers about you implicitly.")

memories = db.table("memories").select("*").eq("user_id", st.session_state.user_id).order("importance_score", desc=True).execute()

for m in memories.data:
    col1, col2, col3 = st.columns([6, 1, 1])
    col1.write(m["content"])
    col2.write(f"Score: {m['importance_score']}")
    if col3.button("Forget", key=m["id"]):
        db.table("memories").delete().eq("id", m["id"]).execute()
        st.rerun()
