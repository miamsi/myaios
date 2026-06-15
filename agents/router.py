from services.groq_client import get_llm
from langchain_core.messages import ToolMessage
from tools.productivity import tools
from services.supabase_client import db
import streamlit as st

class RouterAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = get_llm(temperature=0.2, streaming=False).bind_tools(tools)
        self.stream_llm = get_llm(temperature=0.2, streaming=True)
        self.tool_map = {t.name: t for t in tools}
        try:
            from tavily import TavilyClient
            self.tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
        except: self.tavily = None

    def _get_profile(self) -> str:
        res = db.table("user_profiles").select("*").eq("user_id", self.user_id).execute()
        p = res.data[0] if res.data else {}
        return f"Name: {p.get('name', 'User')} | Lang: {p.get('preferred_language', 'EN')} | TZ: {p.get('timezone', 'UTC')}"

    def execute(self, query, history, mem_ctx, rag_ctx):
        # 1. Jalankan Deteksi Kata Kunci Tavily
        trigger_words = ["search", "current", "hari ini", "sekarang", "berita", "saham", "cuaca", "terbaru", "berapa harga", "ptba"]
        need_search = any(word in query.lower() for word in trigger_words)
            
        if self.tavily and need_search:
            try:
                search_res = self.tavily.search(query=query, search_depth="basic", max_results=3)
                web_ctx = "\n".join([f"- {r['title']}: {r['content']} (Source: {r['url']})" for r in search_res['results']])
            except Exception:
                web_ctx = "Gagal mengambil data real-time dari internet."
        else:
            web_ctx = "Tidak ada referensi internet terbaru."

        # 2. Hancurkan asumsi tool-call bawaan Llama dengan menyatukan teks ke satu prompt statis.
        # Strategi ini mengubah format objek chat biasa menjadi satu kesatuan dokumen instruksi agar Groq bertindak sebagai Penulis/Asisten murni.
        
        system_instruction = (
            "You are a helpful, private AI Operating System assistant. "
            "You MUST reply to the user directly in natural language text. "
            "DO NOT invoke, execute, or mention any internal tools, functions, XML tags, or search tools (like brave_search or wolfram_alpha). "
            "Your tool-calling engine is strictly disabled. Treat everything as a pure reading and text-generation task."
        )

        # Bangun teks percakapan historis agar konteks tetap terjaga
        conversation_history = ""
        for msg in history[-4:]: # Ambil 4 pesan terakhir agar ingatan tetap segar tapi hemat token
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_history += f"{role}: {msg['content']}\n"

        # Gabungkan seluruh data menjadi satu muatan pesan tunggal (User Role)
        final_payload = (
            f"CONTEXT AND GROUND TRUTH DATA:\n"
            f"[Long-term Memory]: {mem_ctx}\n"
            f"[Document Knowledge]: {rag_ctx}\n"
            f"[Live Web Search Result]: {web_ctx}\n\n"
            f"CONVERSATION HISTORY:\n{conversation_history}\n"
            f"CURRENT USER QUESTION: {query}\n\n"
            f"INSTRUCTION: Answer the user question accurately using the live web search results provided above. "
            f"Answer in Indonesian, matching the user's casual tone, and output ONLY the text response."
        )

        # Kirim ke Groq dengan format dua arah yang sangat kaku agar dia tidak punya ruang untuk berhalusinasi
        formatted_messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": final_payload}
        ]

        # 3. Eksekusi
        response = self.llm.invoke(formatted_messages)
        return response
