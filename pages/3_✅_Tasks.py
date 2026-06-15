import streamlit as st
from services.supabase_client import db

st.title("Task Management")

with st.form("new_task"):
    title = st.text_input("Task Title")
    date = st.text_input("Due Date (Optional YYYY-MM-DD)")
    if st.form_submit_button("Add Task"):
        db.table("tasks").insert({"user_id": st.session_state.user_id, "title": title, "due_date": date}).execute()
        st.success("Added!")

tasks = db.table("tasks").select("*").eq("user_id", st.session_state.user_id).eq("status", "todo").execute()
for t in tasks.data:
    col1, col2 = st.columns([4, 1])
    col1.markdown(f"**{t['title']}** (Due: {t['due_date']})")
    if col2.button("Done", key=t['id']):
        db.table("tasks").update({"status": "done"}).eq("id", t["id"]).execute()
        st.rerun()
