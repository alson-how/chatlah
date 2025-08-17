# app/intents.py
from __future__ import annotations
from typing import Dict, List, Tuple

# Intent detection patterns for enhanced conversation flow
PORTFOLIO_TRIGGERS = (
    "portfolio", "past project", "past projects", "projects",
    "work examples", "your work", "case study", "case studies",
    "references", "previous jobs", "gallery", "showroom",
    "examples", "sample", "samples"
)

PRICING_TRIGGERS = (
    "price", "pricing", "cost", "costs", "budget", "how much", 
    "expensive", "cheap", "affordable", "rate", "rates", "fee", "fees"
)

CONSULTATION_TRIGGERS = (
    "consultation", "meeting", "visit", "appointment", "schedule",
    "book", "booking", "when can", "available", "free time"
)

SERVICE_TRIGGERS = (
    "service", "services", "what do you do", "what do you offer",
    "specialization", "specialize", "expertise", "renovation", 
    "design", "interior design"
)

def is_portfolio_intent(text: str) -> bool:
    """Check if user is asking about portfolio/examples."""
    t = (text or "").lower()
    return any(k in t for k in PORTFOLIO_TRIGGERS)

def is_pricing_intent(text: str) -> bool:
    """Check if user is asking about pricing."""
    t = (text or "").lower()
    return any(k in t for k in PRICING_TRIGGERS)

def is_consultation_intent(text: str) -> bool:
    """Check if user wants to schedule consultation."""
    t = (text or "").lower()
    return any(k in t for k in CONSULTATION_TRIGGERS)

def is_service_intent(text: str) -> bool:
    """Check if user is asking about services offered."""
    t = (text or "").lower()
    return any(k in t for k in SERVICE_TRIGGERS)

def detect_intents(text: str) -> List[str]:
    """Detect all applicable intents in user message."""
    intents = []
    
    if is_portfolio_intent(text):
        intents.append("portfolio")
    if is_pricing_intent(text):
        intents.append("pricing")
    if is_consultation_intent(text):
        intents.append("consultation")
    if is_service_intent(text):
        intents.append("service")
        
    return intents

def get_intent_priority(intents: List[str]) -> str:
    """Get highest priority intent for response routing."""
    # Priority order: consultation > portfolio > service > pricing
    priority_order = ["consultation", "portfolio", "service", "pricing"]
    
    for intent in priority_order:
        if intent in intents:
            return intent
            
    return "general"
