import streamlit as st
from agents.knowledge import KnowledgeAgent
from services.supabase_client import db

if "user_id" not in st.session_state:
    st.warning("Secure session missing. Redirecting to main login...")
    st.switch_page("app.py")
    st.stop()

st.title("Knowledge Base")
agent = KnowledgeAgent(st.session_state.user_id)

files = st.file_uploader("Upload: PDF, TXT, MD", accept_multiple_files=True)
if st.button("Index Documents") and files:
    for f in files:
        with st.spinner(f"Indexing {f.name}..."):
            agent.process_and_store(f.read(), f.name, f.type)
    st.success("Indexed.")

st.divider()
docs = db.table("documents").select("id, filename").eq("user_id", st.session_state.user_id).execute()
for doc in docs.data:
    col1, col2 = st.columns([4, 1])
    col1.write(doc["filename"])
    if col2.button("Purge", key=doc["id"]):
        db.table("documents").delete().eq("id", doc["id"]).execute()
        st.rerun()
