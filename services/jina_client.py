import requests
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential

class JinaService:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {st.secrets['JINA_API_KEY']}", "Content-Type": "application/json"}
        self.session = requests.Session()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts: return []
        res = self.session.post("https://api.jina.ai/v1/embeddings", headers=self.headers, json={"model": "jina-embeddings-v3", "input": texts}, timeout=20)
        res.raise_for_status()
        return [item["embedding"] for item in sorted(res.json()["data"], key=lambda x: x["index"])]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def rerank(self, query: str, documents: list[str], top_n: int = 3) -> list[dict]:
        if not documents: return []
        res = self.session.post("https://api.jina.ai/v1/rerank", headers=self.headers, json={"model": "jina-reranker-v2-base-multilingual", "query": query, "documents": documents, "top_n": top_n}, timeout=15)
        res.raise_for_status()
        return res.json()["results"]

@st.cache_resource(show_spinner=False)
def get_jina(): return JinaService()
jina = get_jina()
