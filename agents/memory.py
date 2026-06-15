import json
from services.supabase_client import db
from services.jina_client import jina
from services.groq_client import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

class MemoryAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm = get_llm(temperature=0, streaming=False)

    def extract_and_store(self, text: str):
        sys_prompt = """Analyze the message. 1. Extract general facts (score 1-10). 2. Detect profile data: name, occupation, preferred_language, timezone, communication_style. Respond in STRICT JSON: {"facts": [{"fact": "str", "score": int}], "profile_updates": {"key": "value"}}"""
        try:
            res = self.llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=text)], response_format={"type": "json_object"}).content
            data = json.loads(res)
            
            updates = {k: v for k, v in data.get("profile_updates", {}).items() if v}
            if updates: db.table("user_profiles").update(updates).eq("user_id", self.user_id).execute()

            for f in data.get("facts", []):
                if f.get("score", 0) >= 7 and f.get("fact"):
                    emb = jina.embed([f["fact"]])[0]
                    if not db.rpc("match_memories", {"query_embedding": emb, "target_user_id": self.user_id, "match_threshold": 0.95, "match_count": 1}).execute().data:
                        db.table("memories").insert({"user_id": self.user_id, "content": f["fact"], "importance_score": f["score"], "embedding": emb}).execute()
        except: pass

    def retrieve(self, query: str) -> str:
        emb = jina.embed([query])[0]
        res = db.rpc("match_memories", {"query_embedding": emb, "target_user_id": self.user_id, "match_threshold": 0.6, "match_count": 4}).execute()
        return "\n".join([f"- {r['content']}" for r in res.data]) if res.data else ""
