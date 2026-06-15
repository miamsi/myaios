import streamlit as st
import time
from agents.router import RouterAgent
from agents.memory import MemoryAgent
from agents.knowledge import KnowledgeAgent
from services.supabase_client import db
from services.compression import compress_session_history

# 1. Guardrail Keamanan Sesi
if "user_id" not in st.session_state:
    st.warning("Secure session missing. Redirecting to main login...")
    st.switch_page("app.py")
    st.stop()
    
st.title("Interface")
st.title("Interface")

# === POTONGAN KODE DIAGNOSTIK (Hapus jika sudah normal) ===
import os
st.sidebar.subheader("🔍 API Key Diagnostics")
groq_env = os.environ.get("GROQ_API_KEY")
groq_sec = st.secrets.get("GROQ_API_KEY")

st.sidebar.write("Groq via System Env:", "✅ Terdeteksi" if groq_env else "❌ Kosong")
st.sidebar.write("Groq via St Secrets:", "✅ Terdeteksi" if groq_sec else "❌ Kosong")
# ==========================================================
# 2. Manajemen Sidebar & Sesi Chat
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

# 3. Menampilkan Riwayat Chat Lama
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): 
        st.markdown(msg["content"])

# 4. Memproses Input Chat Baru
if prompt := st.chat_input("Input command or query..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.markdown(prompt)
        
    db.table("chat_messages").insert({
        "session_id": st.session_state.session_id, 
        "role": "user", 
        "content": prompt
    }).execute()

    # Panggil Agen Memori dan Pengetahuan
    mem_agent = MemoryAgent(st.session_state.user_id)
    mem_agent.extract_and_store(prompt) 
    
    mem_ctx = mem_agent.retrieve(prompt)
    rag_ctx = KnowledgeAgent(st.session_state.user_id).search(prompt)

    # --- BLOK PROSES JAWABAN ASISTEN YANG SUDAH DIPERBAIKI ---
    with st.chat_message("assistant"):
        #Ambil Balasan Tunggal dari RouterAgent
        agent_output = RouterAgent(st.session_state.user_id).execute(
            prompt, 
            st.session_state.messages[:-1], 
            mem_ctx, 
            rag_ctx
        )
        
        # Ekstraksi Teks Secara Defensif (Anti-Tuple & Anti-Object Error)
        if hasattr(agent_output, "content"):
            response = agent_output.content
        elif isinstance(agent_output, tuple):
            response = agent_output[1] if len(agent_output) > 1 else str(agent_output)
        else:
            response = str(agent_output)
            
        # Trik Animasi Ketikan (Simulated Streaming) agar UI Tetap Cantik
        def Teks_generator():
            for word in response.split(" "):
                yield word + " "
                time.sleep(0.04)
                
        # Tampilkan teks dengan efek mengetik ke layar Streamlit
        st.write_stream(Teks_generator())
    # --------------------------------------------------------
        
    # Simpan hasil akhir ke database & jalankan kompresi riwayat jika kepenuhan
    st.session_state.messages.append({"role": "assistant", "content": response})
    db.table("chat_messages").insert({
        "session_id": st.session_state.session_id, 
        "role": "assistant", 
        "content": response
    }).execute()
    
    compress_session_history(st.session_state.session_id)
