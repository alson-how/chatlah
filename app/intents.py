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
    SERVICES = auto()
    PRICING = auto()
    GENERIC_ID = auto()
    INFO_REQUEST = auto()
    OFFICE_ADDRESS = auto()
    NONE = auto()


# Intent detection patterns
PORTFOLIO_TRIGGERS = ("portfolio", "past project", "past projects", "projects",
                      "work examples", "your work", "case study",
                      "case studies", "references", "gallery", "showroom",
                      "examples", "sample", "samples")

INFO_TRIGGERS = ("do you", "can you", "how", "what", "price", "cost",
                 "timeline", "lead time", "revision", "portfolio",
                 "past project", "projects", "process", "services", "warranty",
                 "quotation", "quote", "examples", "sample", "consultation")

OFFICE_ADDRESS_TRIGGERS = ("where are you located", "office address",
                           "your address", "your location",
                           "where is your office", "office location",
                           "address", "where you based",
                           "where can I find you", "your office", "location",
                           "where are you")

# Services-specific triggers
SERVICES_TRIGGERS = ("services", "what do you do", "what services", 
                    "interior design services", "your services", "service", 
                    "what can you do", "offerings", "what you offer")

# Pricing-specific triggers (using word boundaries to avoid false matches)
PRICING_TRIGGERS = ("price", "cost", "how much", "pricing", "budget", 
                   "expensive", "cheap", "rate", " fee ", "charge", 
                   "what does it cost", "how much does", "what's the cost")

GENERIC_ID_PATTERN = r"\b(id|interior design|renovation|makeover|concept)\b"


def detect_intent(text: str) -> Intent:
    """Detect the primary intent from user message."""
    if not text:
        return Intent.NONE

    text_lower = text.lower().strip()
    
    # Check if this is likely a style preference response (not a question)
    style_indicators = ['cozy', 'modern', 'minimalist', 'contemporary', 'traditional', 
                       'scandinavian', 'industrial', 'rustic', 'elegant', 'luxury', 
                       'vintage', 'classic', 'warm', 'cool', 'bright', 'feel', 'vibe', 
                       'aesthetic', 'look', 'theme', 'style']
    
    # If it's a short response with style indicators and no explicit pricing words, 
    # don't classify as pricing intent
    is_style_response = (len(text_lower.split()) <= 5 and 
                        any(indicator in text_lower for indicator in style_indicators) and
                        not any(explicit_price in text_lower for explicit_price in 
                               ['how much', 'cost', 'price', 'expensive', 'cheap', 'rate', 'fee', 'charge']))

    # Office address intent has highest priority for location queries
    if any(trigger in text_lower for trigger in OFFICE_ADDRESS_TRIGGERS):
        return Intent.OFFICE_ADDRESS

    # Pricing intent has high priority to handle pricing questions specifically
    # But exclude style responses and use more precise matching
    if not is_style_response:
        # Check for explicit pricing questions with word boundaries
        pricing_match = False
        for trigger in PRICING_TRIGGERS:
            if trigger.strip() == "fee":
                # Special case for "fee" - check if it's a standalone word
                if re.search(r'\bfee\b', text_lower):
                    pricing_match = True
                    break
            elif trigger in text_lower:
                pricing_match = True
                break
        
        if pricing_match:
            return Intent.PRICING
        
    # Services intent to provide services information
    if any(trigger in text_lower for trigger in SERVICES_TRIGGERS):
        return Intent.SERVICES

    # Portfolio intent has high priority
    if any(trigger in text_lower for trigger in PORTFOLIO_TRIGGERS):
        return Intent.PORTFOLIO

    # Generic interior design intent
    if re.search(GENERIC_ID_PATTERN, text, re.I):
        return Intent.GENERIC_ID

    # Information request intent (but exclude style responses)
    if not is_style_response and any(trigger in text_lower for trigger in INFO_TRIGGERS):
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


def handle_portfolio_intent(
        text: str,
        state=None,
        portfolio_url: str = "https://jablancinteriors.com/projects/") -> str:
    """Handle portfolio intent and generate appropriate response with intelligent follow-ups."""
    # Debug: Print the portfolio_url to see what's being passed
    print(f"DEBUG: Portfolio URL received: '{portfolio_url}'")
    
    # Ensure we always have a valid portfolio URL
    if not portfolio_url or portfolio_url.strip() == "":
        portfolio_url = "https://jablancinteriors.com/projects/"
        print(f"DEBUG: Using default portfolio URL: {portfolio_url}")
    
    preview = portfolio_preview()
    head = f"Yes sure, you may look at our portfolio here {portfolio_url}."
    body = f"\n{preview}" if preview else ""

    # Generate intelligent follow-up based on missing information and context
    follow_up = get_intelligent_portfolio_followup(text, state)
    
    response = (head + body).strip()
    if follow_up:
        response += f"\n{follow_up}"

    return response


def get_intelligent_portfolio_followup(user_text: str, state) -> Optional[str]:
    """Generate context-aware follow-up questions after portfolio response."""
    if not state:
        return None

    # Import here to avoid circular imports
    from app.slots import get_missing_required_fields, get_dynamic_field_configs

    missing_fields = get_missing_required_fields(state)
    if not missing_fields:
        return None  # All information collected

    text_lower = user_text.lower()

    # Context-aware follow-ups based on what user is asking about
    if any(keyword in text_lower for keyword in
           ["style", "design", "aesthetic", "look", "vibe", "theme"]):
        if "style" in missing_fields:
            return "What style catches your eye? Modern, minimalist, or something else?"
        elif "location" in missing_fields:
            return "Which area is your property located in?"
        elif "budget" in missing_fields:
            return "What's your budget range for this project?"

    elif any(keyword in text_lower
             for keyword in ["similar", "like this", "same", "type"]):
        if "location" in missing_fields:
            return "Where is your property located? This helps me suggest similar projects in your area."
        elif "style" in missing_fields:
            return "Which style from our portfolio appeals to you most?"
        elif "budget" in missing_fields:
            return "What budget range are you working with?"

    elif any(keyword in text_lower
             for keyword in ["cost", "price", "budget", "expensive"]):
        if "budget" in missing_fields:
            return "What's your allocated budget for this project?"
        elif "location" in missing_fields:
            return "Which area is the property? Location affects pricing and logistics."
        elif "style" in missing_fields:
            return "What design style are you considering?"

    # Smart prioritization based on conversation flow (skip name if already collected)
    field_configs = get_dynamic_field_configs()
    
    # For portfolio follow-ups, prioritize business-relevant fields over personal details
    # Skip name if already collected, focus on project details first
    if state.name:
        priority_order = ["style", "location", "budget", "phone"]
    else:
        priority_order = ["name", "style", "location", "budget", "phone"]

    for field_name in priority_order:
        if field_name in missing_fields:
            # Find the question for this field
            for config in field_configs:
                if config['field_name'] == field_name:
                    if field_name == "style":
                        return "Based on our portfolio, what style direction interests you?"
                    elif field_name == "location":
                        return "Which area is your property located? This helps me recommend relevant projects."
                    elif field_name == "budget":
                        return "What's your budget range? This helps me suggest suitable options."
                    elif field_name == "name":
                        return "May I have your name so I can personalize our consultation?"
                    elif field_name == "phone":
                        return "What's the best number to reach you for follow-up?"
                    else:
                        return config['question_text']

    return None


def portfolio_preview(max_items: int = 3) -> Optional[str]:
    """Show 1–3 project examples from portfolio."""
    # Return static portfolio examples pointing to the correct portfolio URL
    portfolio_examples = [
        "Modern Minimalist Design (https://jablancinteriors.com/projects/)",
        "Contemporary Living Space (https://jablancinteriors.com/projects/)",
        "Scandinavian Style Interior (https://jablancinteriors.com/projects/)"
    ]
    
    # Take only the requested number of examples
    selected_examples = portfolio_examples[:max_items]
    return "Examples: " + "; ".join(selected_examples)


def rag_answer_one_liner(user_text: str,
                         max_chars: int = 220,
                         state=None) -> Optional[str]:
    """Answer side-questions briefly using RAG (1 sentence + 1 source)."""
    if not is_info_request_intent(user_text):
        return None

    # Check if we have the user's name before providing detailed information
    if state and not getattr(state, 'name', None):
        return None  # Don't provide RAG info without name

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
        "office address location contact", "where located address",
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


def respond_with_intent(
    intent: Intent,
    user_text: str,
    state,
    portfolio_url: str = "https://jablancinteriors.com/projects/"
) -> Optional[str]:
    """Generate response based on detected intent."""
    if intent == Intent.SERVICES:
        # Handle services inquiry - provide services info first, then ask for name
        services_info = get_services_info_from_rag()
        follow_up = "May I have your name and phone number so I can follow up properly?"
        return f"{services_info}\n{follow_up}"
        
    elif intent == Intent.PRICING:
        # Handle pricing inquiry with standard response
        return "It's depending on the style you want. Let's talk more when we meet. May I have your name and phone number so I can follow up properly?"
        
    elif intent == Intent.PORTFOLIO:
        # Use optimized portfolio handler with intelligent follow-ups
        return handle_portfolio_intent(user_text, state, portfolio_url)

    elif intent == Intent.OFFICE_ADDRESS:
        address_info = get_office_address_from_rag(user_text)
        if address_info:
            # Use intelligent follow-up for office address queries too
            follow_up = get_intelligent_portfolio_followup(user_text, state)
            return address_info + (f"\n{follow_up}" if follow_up else "")
        return "Please contact us for our office address details."

    elif intent == Intent.INFO_REQUEST:
        # Check if we have the user's name before providing detailed information
        if not state.name:
            return "Before that, can I know who am I speaking to?"
        return rag_answer_one_liner(user_text, state=state)

    return None


def get_services_info_from_rag() -> str:
    """Get services information from RAG or provide default services info."""
    # Clean fallback services description with proper link
    return "Hi there, this is Mei Yee from Jablanc Interior. We offer comprehensive interior design services including space planning, renovation, furniture selection, and complete home makeovers. Check out our full services: https://jablancinteriors.com/services/"
