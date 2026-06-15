from services.supabase_client import db
from services.groq_client import get_llm
from langchain_core.messages import HumanMessage

def compress_session_history(session_id: str):
    msgs = db.table("chat_messages").select("id, role, content").eq("session_id", session_id).order("created_at").execute().data
    if len(msgs) <= 10: return

    session = db.table("chat_sessions").select("summary").eq("id", session_id).execute().data[0]
    current_summary = session.get("summary") or "No previous summary."
    to_compress, keep = msgs[:-4], msgs[-4:]
    transcript = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in to_compress])
    
    prompt = f"Combine previous summary and new transcript into a condensed summary of facts.\nPrevious: {current_summary}\nTranscript: {transcript}"
    new_summary = get_llm(temperature=0, streaming=False).invoke([HumanMessage(content=prompt)]).content
    
    db.table("chat_sessions").update({"summary": new_summary}).eq("id", session_id).execute()
    db.table("chat_messages").delete().in_("id", [m["id"] for m in to_compress]).execute()
