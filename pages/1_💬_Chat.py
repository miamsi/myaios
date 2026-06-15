import streamlit as st
from agents.router import RouterAgent
from agents.memory import MemoryAgent
from agents.knowledge import KnowledgeAgent
from services.supabase_client import db
from services.compression import compress_session_history

if "user_id" not in st.session_state:
    st.warning("Secure session missing. Redirecting to main login...")
    st.switch_page("app.py")
    st.stop()
    
st.title("Interface")

st.sidebar.title("Chats")
if st.sidebar.button("➕ New Chat"):
    res = db.table("chat_sessions").insert({"user_id": st.session_state.user_id}).execute()
    st.session_state.session_id = res.data[0]["id"]
    st.session_state.messages = []
    st.rerun()

sessions = db.table("chat_sessions").select("id, title").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute()
for s in sessions.data:
    if st.sidebar.button(s["title"] or "New Chat", key=s["id"]):
        st.session_state.session_id = s["id"]
        msgs = db.table("chat_messages").select("role, content").eq("session_id", s["id"]).order("created_at").execute()
        st.session_state.messages = msgs.data
        st.rerun()

if "session_id" not in st.session_state:
    res = db.table("chat_sessions").insert({"user_id": st.session_state.user_id}).execute()
    st.session_state.session_id = res.data[0]["id"]
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Input command or query..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    db.table("chat_messages").insert({"session_id": st.session_state.session_id, "role": "user", "content": prompt}).execute()

    mem_agent = MemoryAgent(st.session_state.user_id)
    mem_agent.extract_and_store(prompt) 
    
    mem_ctx = mem_agent.retrieve(prompt)
    rag_ctx = KnowledgeAgent(st.session_state.user_id).search(prompt)

    with st.chat_message("assistant"):
        stream = RouterAgent(st.session_state.user_id).execute(prompt, st.session_state.messages[:-1], mem_ctx, rag_ctx)
        response = st.write_stream((chunk.content for chunk in stream))
        
    st.session_state.messages.append({"role": "assistant", "content": response})
    db.table("chat_messages").insert({"session_id": st.session_state.session_id, "role": "assistant", "content": response}).execute()
    compress_session_history(st.session_state.session_id)
