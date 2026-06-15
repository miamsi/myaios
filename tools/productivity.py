from langchain_core.tools import tool
from services.supabase_client import db
import streamlit as st

@tool
def create_task(title: str, due_date: str = None, priority: str = "medium") -> str:
    """Creates a task. due_date must be YYYY-MM-DD if provided."""
    try:
        db.table("tasks").insert({"user_id": st.session_state.user_id, "title": title, "due_date": due_date, "priority": priority, "status": "todo"}).execute()
        return f"Task '{title}' created successfully."
    except Exception as e: return f"Error creating task: {str(e)}"

@tool
def list_tasks() -> str:
    """Retrieves all pending tasks."""
    try:
        res = db.table("tasks").select("title, due_date, priority").eq("user_id", st.session_state.user_id).eq("status", "todo").execute()
        if not res.data: return "No pending tasks."
        return "\n".join([f"- {t['title']} (Due: {t['due_date']}, Priority: {t['priority']})" for t in res.data])
    except Exception as e: return f"Error fetching tasks: {str(e)}"

tools = [create_task, list_tasks]
