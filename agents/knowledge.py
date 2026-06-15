from services.supabase_client import db
from services.jina_client import jina
from langchain_text_splitters import RecursiveCharacterTextSplitter
import streamlit as st
import fitz

class KnowledgeAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)

    def process_and_store(self, file_bytes: bytes, filename: str, file_type: str):
        text = ""
        if "pdf" in file_type:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc: text += page.get_text()
        else:
            text = file_bytes.decode('utf-8', errors='ignore')

        chunks = self.splitter.split_text(text)
        doc_res = db.table("documents").insert({"user_id": self.user_id, "filename": filename, "file_type": file_type}).execute()
        doc_id = doc_res.data[0]["id"]

        for i in range(0, len(chunks), 50):
            batch = chunks[i:i+50]
            embeddings = jina.embed(batch)
            payload = [{"document_id": doc_id, "content": c, "chunk_index": i+j, "embedding": e} for j, (c, e) in enumerate(zip(batch, embeddings))]
            db.table("document_chunks").insert(payload).execute()

    @st.cache_data(ttl=300, show_spinner=False)
    def search(_self, query: str) -> str:
        query_emb = jina.embed([query])[0]
        res = db.rpc("match_document_chunks", {"query_embedding": query_emb, "target_user_id": _self.user_id, "match_threshold": 0.5, "match_count": 10}).execute()
        if not res.data: return ""
        
        docs = [r["content"] for r in res.data]
        reranked = jina.rerank(query, docs, top_n=3)
        return "\n\n".join([f"[Source: {res.data[item['index']]['filename']}]\n{res.data[item['index']]['content']}" for item in reranked])
