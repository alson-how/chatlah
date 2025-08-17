# app/rag_assist.py
from typing import Optional
from app.retriever import search
from app.intents import detect_intents, get_intent_priority, is_portfolio_intent
from app.portfolio_preview import portfolio_preview

INFO_TRIGGERS = ("do you", "can you", "how", "what", "price", "timeline", "revision",
                 "portfolio", "process", "services", "warranty", "quotation", "quote",
                 "examples", "sample", "consultation", "appointment", "meeting")

def maybe_answer_with_rag(user_text: str, max_chars: int = 220) -> Optional[str]:
    """Enhanced RAG assistant with intent detection and portfolio preview."""
    t = user_text.lower()
    
    # First check for portfolio intent and provide preview if applicable
    if is_portfolio_intent(user_text):
        portfolio = portfolio_preview(max_items=3)
        if portfolio:
            # Still search for relevant content to add context
            hits = search(user_text, top_k=1)
            if hits:
                context_snippet = hits[0]["text"][:150].rsplit(" ", 1)[0] + "..."
                return f"{context_snippet}\n\n{portfolio}"
            else:
                return f"Here are some of our portfolio examples:\n{portfolio}"
    
    # Check for other information queries
    if not any(k in t for k in INFO_TRIGGERS):
        return None
        
    hits = search(user_text, top_k=2) or []
    if not hits: 
        return None
        
    h = hits[0]
    url = h["meta"].get("url", "")
    snippet = (h["text"] or "").strip()
    
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rsplit(" ", 1)[0] + "..."
        
    # Detect additional intents to enhance response
    intents = detect_intents(user_text)
    priority_intent = get_intent_priority(intents)
    
    # Add context-aware response based on intent
    if priority_intent == "consultation":
        snippet += "\n\nWould you like to schedule a consultation to discuss your project in detail?"
    elif priority_intent == "pricing":
        snippet += "\n\nFor a detailed quote, we'd need to understand your specific requirements."
    
    return f"{snippet}" + (f" (Source: {url})" if url else "")
