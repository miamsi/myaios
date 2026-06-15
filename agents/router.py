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

    def execute(self, query: str, history: list, mem_context: str, rag_context: str):
        sys_prompt = f"You are a Personal AI OS. Prioritize accuracy and helpfulness.\n### PROFILE\n{self._get_profile()}"
        if mem_context: sys_prompt += f"\n\n### MEMORY\n{mem_context}"
        if rag_context: sys_prompt += f"\n\n### KNOWLEDGE\n{rag_context}"
        
        messages = [{"role": "system", "content": sys_prompt}] + history + [{"role": "user", "content": query}]
        response = self.llm.invoke(messages)
        
        if response.tool_calls:
            messages.append(response)
            for call in response.tool_calls:
                messages.append(ToolMessage(content=self.tool_map[call["name"]].invoke(call["args"]), tool_call_id=call["id"]))
            return self.stream_llm.stream(messages)
            
        # 1. Jalankan Deteksi Kata Kunci Tavily seperti sebelumnya
        trigger_words = ["search", "current", "hari ini", "sekarang", "berita", "saham", "cuaca", "terbaru", "berapa harga"]
        need_search = any(word in query.lower() for word in trigger_words)
            
        if self.tavily and need_search:
            try:
                search_res = self.tavily.search(query=query, search_depth="basic", max_results=3)
                web_ctx = "\n".join([f"- {r['title']}: {r['content']} (Source: {r['url']})" for r in search_res['results']])
            except Exception:
                web_ctx = "Gagal mengambil data dari internet."
        else:
            web_ctx = "Tidak ada data internet terbaru."

        # 2. Susun pesan yang bersih untuk Groq (Taruh konteks di akhir agar dibaca maksimal)
        formatted_messages = []
        
        # Masukkan seluruh riwayat chat sebelumnya
        for msg in history:
            formatted_messages.append(msg)
            
        # Buat System/User Hint terakhir agar Groq TIDAK memanggil tool internal
        final_prompt = f"USER QUERY: {query}\n\n"
        final_prompt += f"### LIVE WEB CONTEXT (Gunakan data ini untuk menjawab, JANGAN memanggil fungsi/tool search eksternal lagi):\n{web_ctx}\n\n"
        final_prompt += "Silakan jawab pertanyaan user langsung dalam bentuk teks biasa berdasarkan konteks di atas."
        
        # Masukkan prompt akhir ini sebagai pesan User terakhir
        formatted_messages.append({"role": "user", "content": final_prompt})

        # 3. Panggil LLM dengan struktur pesan yang baru
        response = self.llm.invoke(formatted_messages)
        return response
