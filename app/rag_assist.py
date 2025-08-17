# rag_assist.py
from typing import Optional
from app.retriever import search

INFO_TRIGGERS = (
    "do you", "can you", "how", "what", "price", "timeline", "revision",
    "portfolio", "past project", "projects", "process", "services", "quote"
)

def maybe_rag_line(user_text: str, max_chars: int = 220) -> Optional[str]:
    t = (user_text or "").lower()
    if not any(k in t for k in INFO_TRIGGERS):
        return None
    hits = search(user_text, top_k=2) or []
    if not hits: return None
    h = hits[0]
    url = h["meta"].get("url", "")
    snippet = (h["text"] or "").strip()
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rsplit(" ", 1)[0] + "..."
    return f"{snippet} (Source: {url})"
