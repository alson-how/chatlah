"""
Intent detection and handling for conversational AI.
Manages detection of user intents like portfolio requests, generic ID queries, and information requests.
"""

import re
from typing import Optional
from enum import Enum, auto
from app.retriever import search

class Intent(Enum):
    PORTFOLIO = auto()
    GENERIC_ID = auto()
    INFO_REQUEST = auto()
    OFFICE_ADDRESS = auto()
    NONE = auto()

# Intent detection patterns
PORTFOLIO_TRIGGERS = (
    "portfolio", "past project", "past projects", "projects",
    "work examples", "your work", "case study", "case studies", 
    "references", "gallery", "showroom", "examples", "sample", "samples"
)

INFO_TRIGGERS = (
    "do you", "can you", "how", "what", "price", "cost", "timeline", "lead time",
    "revision", "portfolio", "past project", "projects", "process", "services",
    "warranty", "quotation", "quote", "examples", "sample", "consultation"
)

OFFICE_ADDRESS_TRIGGERS = (
    "where are you located", "office address", "your address", "your location",
    "where is your office", "office location", "address", "where you based",
    "where can I find you", "your office", "location", "where are you"
)

GENERIC_ID_PATTERN = r"\b(id|interior design|renovation|makeover|concept)\b"

def detect_intent(text: str) -> Intent:
    """Detect the primary intent from user message."""
    if not text:
        return Intent.NONE
    
    text_lower = text.lower()
    
    # Office address intent has highest priority for location queries
    if any(trigger in text_lower for trigger in OFFICE_ADDRESS_TRIGGERS):
        return Intent.OFFICE_ADDRESS
    
    # Portfolio intent has high priority
    if any(trigger in text_lower for trigger in PORTFOLIO_TRIGGERS):
        return Intent.PORTFOLIO
    
    # Generic interior design intent
    if re.search(GENERIC_ID_PATTERN, text, re.I):
        return Intent.GENERIC_ID
    
    # Information request intent
    if any(trigger in text_lower for trigger in INFO_TRIGGERS):
        return Intent.INFO_REQUEST
    
    return Intent.NONE

def is_portfolio_intent(text: str) -> bool:
    """Check if text contains portfolio-related intent."""
    return detect_intent(text) == Intent.PORTFOLIO

def is_generic_id_intent(text: str) -> bool:
    """Check if text contains generic interior design intent."""
    return detect_intent(text) == Intent.GENERIC_ID

def is_info_request_intent(text: str) -> bool:
    """Check if text contains information request intent."""
    return detect_intent(text) == Intent.INFO_REQUEST

def is_office_address_intent(text: str) -> bool:
    """Check if text contains office address intent."""
    return detect_intent(text) == Intent.OFFICE_ADDRESS

def handle_portfolio_intent(text: str, portfolio_url: str = "https://jablancinteriors.com/projects/") -> str:
    """Handle portfolio intent and generate appropriate response."""
    preview = portfolio_preview()
    head = f"Yes sure, you may look at our portfolio here {portfolio_url}."
    body = f"\n{preview}" if preview else ""
    return (head + body).strip()

def portfolio_preview(max_items: int = 3) -> Optional[str]:
    """Show 1–3 project examples from portfolio."""
    hits = search("portfolio projects interior design examples", top_k=max_items) or []
    if not hits:
        return None
    
    items = []
    for h in hits:
        title = (h["meta"].get("title") or "").strip()
        url = h["meta"].get("url") or ""
        if title and url:
            items.append(f"{title} ({url})")
        elif url:
            items.append(url)
        if len(items) >= max_items:
            break
    
    return "Examples: " + "; ".join(items) if items else None

def rag_answer_one_liner(user_text: str, max_chars: int = 220) -> Optional[str]:
    """Answer side-questions briefly using RAG (1 sentence + 1 source)."""
    if not is_info_request_intent(user_text):
        return None
    
    hits = search(user_text, top_k=2) or []
    if not hits:
        return None
    
    h = hits[0]
    url = h["meta"].get("url", "")
    snippet = (h["text"] or "").strip()
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rsplit(" ", 1)[0] + "..."
    
    return f"{snippet} (Source: {url})"

def get_office_address_from_rag(user_text: str) -> Optional[str]:
    """Get office address information from RAG."""
    # Search for office address information
    address_queries = [
        "office address location contact",
        "where located address",
        "office location address contact information"
    ]
    
    for query in address_queries:
        hits = search(query, top_k=3) or []
        for hit in hits:
            content = (hit["text"] or "").lower()
            url = hit["meta"].get("url", "")
            
            # Look for address patterns in the content
            if any(addr_indicator in content for addr_indicator in [
                "address", "located", "office", "visit", "jalan", "road", 
                "kuala lumpur", "kl", "malaysia", "contact", "ampang"
            ]):
                snippet = (hit["text"] or "").strip()
                if len(snippet) > 300:
                    snippet = snippet[:300].rsplit(" ", 1)[0] + "..."
                return f"{snippet} (Source: {url})"
    
    return None

def respond_with_intent(intent: Intent, user_text: str, state, portfolio_url: str = "https://jablancinteriors.com/projects/") -> Optional[str]:
    """Generate response based on detected intent."""
    if intent == Intent.PORTFOLIO:
        from app.slots import next_missing_after_portfolio
        response = handle_portfolio_intent(user_text, portfolio_url)
        follow_up = next_missing_after_portfolio(state)
        return response + (f"\n{follow_up}" if follow_up else "")
    
    elif intent == Intent.OFFICE_ADDRESS:
        address_info = get_office_address_from_rag(user_text)
        if address_info:
            from app.slots import next_missing_after_portfolio
            follow_up = next_missing_after_portfolio(state)
            return address_info + (f"\n{follow_up}" if follow_up else "")
        return "Please contact us for our office address details."
    
    elif intent == Intent.INFO_REQUEST:
        return rag_answer_one_liner(user_text)
    
    return None