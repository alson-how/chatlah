from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.models import AskRequest, AskResponse, CrawlRequest, CrawlResponse, ChatRequest, ChatResponse
from app.retriever import search
from app.indexer import upsert_chunks
from app.chunking import TextChunker
from app.config import OPENAI_API_KEY
from crawler.firecrawl_crawl import FirecrawlClient
from chromadb import PersistentClient
from utils.theme import mentions_theme, resolve_theme_url
from utils.lead import extract_name, extract_phone, is_lead_only
from utils.location import extract_location, mentions_location_need
from app.database import save_lead, get_lead, get_all_leads, get_merchant_config
from .mcp_tools import router as mcp_router
import requests
import time
import os
import re
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, asdict
from enum import Enum, auto

app = FastAPI(title="RAG Site API", version="1.0.0")
app.include_router(mcp_router)

# Include merchant router
from app.merchant_api import router as merchant_router
app.include_router(merchant_router, prefix="/api/v1")

# Include admin router
from admin.admin_api import router as admin_router
app.include_router(admin_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize ChromaDB client for chat functionality
try:
    chroma_client = PersistentClient(path="./data/chroma")
    try:
        chroma_collection = chroma_client.get_collection("docs")
    except:
        chroma_collection = None  # Will be created when first document is indexed
except Exception:
    chroma_client = None
    chroma_collection = None

# In-memory session store (replace with Redis/DB in prod)
CHAT_SESSIONS = {
}  # {thread_id: {"summary": str, "turns": [(role, content), ...], "first_turn": bool, "name": str, "phone": str}}

# Enhanced Conversation Management Configuration
PORTFOLIO_URL = "https://jablancinteriors.com/projects/"

# Short RAG answer triggers - enhanced with more patterns
INFO_TRIGGERS = (
    "do you", "can you", "how", "what", "price", "cost", "timeline", "lead time",
    "revision", "portfolio", "past project", "projects", "process", "services",
    "warranty", "quotation", "quote", "examples", "sample", "consultation"
)

# Rotating phone prompts for natural variation
PHONE_PROMPTS = [
    "What's the best phone number to reach you?",
    "Could you share a contact number so I can follow up properly?",
    "Mind sharing your phone number? I'll WhatsApp you the next steps.",
]

# Enhanced slot-driven conversation model
class Slot(Enum):
    NAME = auto()
    PHONE = auto()
    STYLE = auto()
    LOCATION = auto()
    SCOPE = auto()
    NONE = auto()

SLOT_QUESTIONS: Dict[Slot, str] = {
    Slot.NAME:     "May I have your name?",
    Slot.PHONE:    "What's the best phone number to reach you?",
    Slot.STYLE:    "What kind of style or vibe you want?",
    Slot.LOCATION: "Which area is the property located?",
    Slot.SCOPE:    "Which spaces are in scope? For example, living, kitchen, master bedroom."
}

# Appointment scheduling messages
APPOINTMENT_MESSAGES = [
    "Perfect! I have your details - {name}, {phone}, {style} style in {location}.",
    "Let me schedule a consultation for you. When would be a good time this week?",
    "I can arrange a site visit - would morning or afternoon work better?",
    "Our designer will contact you within 24 hours to arrange a meeting.",
    "Would you prefer a weekday or weekend appointment for the consultation?"
]

@dataclass
class EnhancedConversationState:
    user_id: str
    lead_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    style: Optional[str] = None
    location: Optional[str] = None
    scope: Optional[str] = None
    
    # Enhanced phone ask control
    asked_phone_count: int = 0
    last_phone_prompt_turn: int = -1
    
    # Generic control
    asked_name_phone_once: bool = False
    turn_index: int = 0
    
    def next_slot(self) -> Slot:
        if not self.name:     return Slot.NAME
        if not self.phone:    return Slot.PHONE
        if not self.style:    return Slot.STYLE
        if not self.location: return Slot.LOCATION
        if not self.scope:    return Slot.SCOPE
        return Slot.NONE
    
    def is_ready_for_appointment(self) -> bool:
        """Check if we have minimum required info for appointment booking."""
        return bool(self.name and self.phone and self.style and self.location)
    
    def to_dict(self): 
        return asdict(self)

# Enhanced intent detection
PORTFOLIO_TRIGGERS = (
    "portfolio", "past project", "past projects", "projects",
    "work examples", "your work", "case study", "case studies", 
    "references", "gallery", "showroom", "examples", "sample", "samples"
)

def is_portfolio_intent(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in PORTFOLIO_TRIGGERS)

def is_generic_id_intent(text: str) -> bool:
    return bool(re.search(r"\b(id|interior design|renovation|makeover|concept)\b", (text or ""), re.I))

# Enhanced RAG helpers with portfolio preview
def rag_answer_one_liner(user_text: str, max_chars: int = 220) -> Optional[str]:
    """Answer side-questions briefly using RAG (1 sentence + 1 source)."""
    t = (user_text or "").lower()
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
    return f"{snippet} (Source: {url})"

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

# Enhanced phone ask policy with cooldown and rotations
def next_phone_prompt(state: EnhancedConversationState) -> Optional[str]:
    # Cooldown: don't repeat within 2 turns
    if state.asked_phone_count > 0 and (state.turn_index - state.last_phone_prompt_turn) < 2:
        return None
    # Stop after 3 attempts; keep progressing other slots
    if state.asked_phone_count >= 3:
        return None
    variant = PHONE_PROMPTS[state.asked_phone_count % len(PHONE_PROMPTS)]
    if state.name:
        variant = f"Thanks, {state.name}. {variant}"
    return variant

def mark_phone_prompted(state: EnhancedConversationState):
    state.asked_phone_count += 1
    state.last_phone_prompt_turn = state.turn_index

# Enhanced follow-up question helpers
def next_missing_after_portfolio(state) -> Optional[str]:
    """Get next missing field question after portfolio interaction."""
    if hasattr(state, 'style'):
        if not state.style:    return SLOT_QUESTIONS[Slot.STYLE]
        if not state.location: return SLOT_QUESTIONS[Slot.LOCATION]
        if not state.phone:    return SLOT_QUESTIONS[Slot.PHONE]
    else:
        # Fallback for legacy state objects
        if not getattr(state, 'style', None):
            return "What kind of style or vibe you want?"
        if not getattr(state, 'location', None):
            return "Which area is the property located?"
        if not getattr(state, 'phone', None):
            return "What's the best phone number to reach you?"
    return None

def next_non_phone_slot_question(state) -> Optional[str]:
    """Get next non-phone field question for conversation flow."""
    if hasattr(state, 'style'):
        if not state.style:    return SLOT_QUESTIONS[Slot.STYLE]
        if not state.location: return SLOT_QUESTIONS[Slot.LOCATION]
        if not state.scope:    return SLOT_QUESTIONS[Slot.SCOPE]
    else:
        # Fallback for legacy state objects
        if not getattr(state, 'style', None):
            return "What kind of style or vibe you want?"
        if not getattr(state, 'location', None):
            return "Which area is the property located?"
    return None

# Enhanced late capture function
def enhanced_late_capture(user_text: str, state: EnhancedConversationState) -> None:
    """Extract details from any turn and update state."""
    # Name extraction
    try:
        name, name_score = extract_name(user_text)
        if name and name_score >= 2 and not state.name:
            state.name = name
    except (ValueError, TypeError):
        pass
    
    # Phone extraction
    phone = extract_phone(user_text)
    if phone and not state.phone:
        state.phone = phone
    
    # Style & Location extraction
    try:
        from utils.parser_my_style_location import parse_message
        parsed = parse_message(user_text)
        if parsed.get("style_theme") and not state.style:
            state.style = parsed["style_theme"]
        if parsed.get("location") and not state.location:
            state.location = parsed["location"]
    except ImportError:
        # Fallback to basic location extraction
        location = extract_location(user_text)
        if location and not state.location:
            state.location = location

# Core enhanced controller
REASK_PREFIX = "Just to confirm,"

def get_dynamic_field_configs():
    """Get field configurations from admin settings."""
    try:
        from admin.admin_database import get_active_field_configs
        return get_active_field_configs()
    except Exception as e:
        print(f"Error loading field configs: {e}")
        # Fallback to default configuration
        return [
            {'field_name': 'name', 'question_text': 'May I have your name?', 'is_required': True, 'sort_order': 1},
            {'field_name': 'phone', 'question_text': 'What\'s the best phone number to reach you?', 'is_required': True, 'sort_order': 2},
            {'field_name': 'style', 'question_text': 'What kind of style or vibe you want?', 'is_required': True, 'sort_order': 3},
            {'field_name': 'location', 'question_text': 'Which area is the property located?', 'is_required': True, 'sort_order': 4},
            {'field_name': 'scope', 'question_text': 'Which spaces are in scope? For example, living, kitchen, master bedroom.', 'is_required': False, 'sort_order': 5}
        ]

def dynamic_next_slot(state: EnhancedConversationState) -> Optional[str]:
    """Get next missing required field based on admin configuration."""
    field_configs = get_dynamic_field_configs()
    required_fields = [f for f in field_configs if f['is_required']]
    required_fields.sort(key=lambda x: x['sort_order'])
    
    for field_config in required_fields:
        field_name = field_config['field_name']
        if not getattr(state, field_name, None):
            return field_config['question_text']
    
    return None

def is_ready_for_appointment_dynamic(state: EnhancedConversationState) -> bool:
    """Check if all required fields are collected based on admin configuration."""
    field_configs = get_dynamic_field_configs()
    required_fields = [f for f in field_configs if f['is_required']]
    
    for field_config in required_fields:
        field_name = field_config['field_name']
        if not getattr(state, field_name, None):
            return False
    
    return True

def enhanced_handle_turn(user_text: str, state: EnhancedConversationState) -> str:
    """Enhanced slot-driven conversation handler with RAG integration and appointment scheduling."""
    state.turn_index += 1

    # 1) Late-capture anything provided this turn
    enhanced_late_capture(user_text, state)

    # 2) Check if ready for appointment after capture using dynamic config
    if is_ready_for_appointment_dynamic(state):
        # We have all required fields - proceed to appointment
        import random
        appointment_msg = random.choice(APPOINTMENT_MESSAGES)
        return appointment_msg.format(
            name=state.name or 'there',
            phone=state.phone or 'your contact',
            style=getattr(state, 'style', 'your preferred style') or 'your preferred style',
            location=getattr(state, 'location', 'your location') or 'your location'
        )

    # 3) High-priority: Portfolio intent (always answer first)
    if is_portfolio_intent(user_text):
        preview = portfolio_preview()
        head = f"Yes sure, you may look at our portfolio here {PORTFOLIO_URL}."
        body = f"\n{preview}" if preview else ""
        follow = next_missing_after_portfolio(state)
        return (head + body + (f"\n{follow}" if follow else "")).strip()

    # 4) Determine current slot
    slot = state.next_slot()

    # 5) If user expressed generic ID intent but we're still missing style, probe style first
    if slot in (Slot.NAME, Slot.PHONE) and is_generic_id_intent(user_text) and not state.style:
        rag_line = rag_answer_one_liner(user_text) or ""
        style_probe = SLOT_QUESTIONS[Slot.STYLE]
        return (rag_line + ("\n" if rag_line else "") + style_probe).strip()

    # 6) Check if user answered current slot this turn - use dynamic slot checking
    next_question = dynamic_next_slot(state)
    if not next_question:
        # Check for appointment readiness after slot progression
        if is_ready_for_appointment_dynamic(state):
            import random
            appointment_msg = random.choice(APPOINTMENT_MESSAGES)
            return appointment_msg.format(
                name=state.name or 'there',
                phone=state.phone or 'your contact',
                style=getattr(state, 'style', 'your preferred style') or 'your preferred style',
                location=getattr(state, 'location', 'your location') or 'your location'
            )
        
        # Optional: if style was just captured, send matching project link
        if hasattr(state, 'style') and state.style and mentions_theme(user_text):
            link = resolve_theme_url(user_text)
            if link:
                return f"Sure—here's one project that fits: {link}\nWhat else would you like to know?"
        
        return "Thank you for providing all the information! Our team will be in touch soon."
    
    # If there's a next question to ask, check if it's different from what we would have asked before
    if next_question and next_question != SLOT_QUESTIONS.get(slot, ""):
        return next_question

    # 7) Enhanced off-topic handling with smart phone policy
    rag_line = rag_answer_one_liner(user_text)
    hint = ""
    if slot == Slot.STYLE:    hint = " For example, modern minimalist, warm neutral, or industrial."
    if slot == Slot.LOCATION: hint = " For example, Mont Kiara, Bangsar, or Penang."
    if slot == Slot.SCOPE:    hint = " For example, living and kitchen."
    question = SLOT_QUESTIONS[slot] + hint

    if slot == Slot.PHONE and not state.phone:
        phone_prompt = next_phone_prompt(state)
        if rag_line and phone_prompt:
            mark_phone_prompted(state)
            return f"{rag_line}\n{phone_prompt}"
        if rag_line and not phone_prompt:
            nxt = next_non_phone_slot_question(state)
            return f"{rag_line}\n{nxt}" if nxt else rag_line
        if (not rag_line) and phone_prompt:
            mark_phone_prompted(state)
            return phone_prompt
        # Cooldown active: progress other slots
        nxt = next_non_phone_slot_question(state)
        if nxt:
            return nxt
        return "Share your contact whenever convenient and I'll send the next steps."

    # Non-phone slots: answer side-topic briefly then re-ask
    if rag_line:
        return f"{rag_line}\n{REASK_PREFIX} {question}"
    return question

# Enhanced session management for legacy compatibility
ENHANCED_SESSIONS: Dict[str, EnhancedConversationState] = {}

def get_enhanced_state(user_id: str) -> EnhancedConversationState:
    """Get enhanced conversation state for a user."""
    if user_id not in ENHANCED_SESSIONS:
        ENHANCED_SESSIONS[user_id] = EnhancedConversationState(user_id=user_id)
    return ENHANCED_SESSIONS[user_id]

# Enhanced ask endpoint using the optimized controller
@app.post("/ask_enhanced")
async def enhanced_ask(payload: dict):
    """
    Enhanced ask endpoint with slot-driven conversation management.
    Expected payload: { "user_id": "<phone_or_whatsapp_id>", "text": "<user message>" }
    """
    user_id = payload.get("user_id", "anon")
    text = payload.get("text", "")
    
    state = get_enhanced_state(user_id)
    reply = enhanced_handle_turn(text, state)
    
    return {
        "reply": reply, 
        "state": state.to_dict(),
        "current_slot": state.next_slot().name,
        "completion_progress": {
            "name": bool(state.name),
            "phone": bool(state.phone),
            "style": bool(state.style),
            "location": bool(state.location),
            "scope": bool(state.scope)
        }
    }


@app.get("/")
async def root():
    """Serve the main web interface."""
    return FileResponse("static/index.html")


@app.get("/chat")
async def chat():
    """Serve the chat interface."""
    return FileResponse("static/chat.html")


@app.get("/leads-dashboard")
async def leads_dashboard():
    """Serve the leads dashboard interface."""
    return FileResponse("static/leads.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/leads")
def leads_endpoint():
    """Get all leads from database"""
    try:
        leads = get_all_leads()
        return {"leads": leads, "count": len(leads)}
    except Exception as e:
        return {"error": str(e), "leads": [], "count": 0}


def load_system_prompt(tone_type: str = "customer_support") -> str:
    """Load system prompt from tone file."""
    tone_file = f"tone/{tone_type}.txt"
    try:
        with open(tone_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to customer_support if specified tone doesn't exist
        try:
            with open("tone/customer_support.txt", 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            # Ultimate fallback if no tone files exist
            return (
                "You are a company knowledge assistant. "
                "Answer ONLY using the provided context. "
                "If the answer isn't in context, say you don't have that information. "
                "Cite sources by listing their URLs at the end.")


def call_chat(messages, temperature=0.2, max_tokens=None):
    try:
        json_data = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": temperature
        }
        if max_tokens:
            json_data["max_tokens"] = max_tokens

        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers={
                              "Authorization": f"Bearer {OPENAI_API_KEY}",
                              "Content-Type": "application/json"
                          },
                          json=json_data,
                          timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 503:
            return "I'm temporarily unable to respond due to high demand. Please try again in a moment."
        raise e


def is_greeting(txt: str) -> bool:
    return bool(
        re.match(
            r'^\s*(hi|hello|hey|morning|good (morning|afternoon|evening))\b',
            txt.strip(), re.I))


def postprocess(text: str, first_turn: bool) -> str:
    # remove exclamation marks, overly generic assistant phrasing
    text = re.sub(r'\bassist you\b', 'help you', text,
                  flags=re.I).replace('!', '').strip()
    if not first_turn:
        text = re.sub(r'^\s*(hi|hello|hey)[^a-z0-9]+', '', text,
                      flags=re.I).strip()
    # cap 2 sentences
    parts = re.split(r'(?<=[.?!])\s+', text)
    return ' '.join(parts[:2]).strip()


def summarise(previous_summary, user_msg, assistant_msg):
    prompt = f"""Update the conversation summary (<=500 tokens), capturing user intent, decisions, names,
preferences, and open items. First-person where relevant; no greetings.

previous_summary:
{previous_summary or ''}

latest_user:
{user_msg}

latest_assistant:
{assistant_msg}
"""
    try:
        out = call_chat([{
            "role":
            "system",
            "content":
            "You maintain a compact memory for continuity. Return only the updated summary."
        }, {
            "role": "user",
            "content": prompt
        }],
                        max_tokens=400)
        return out
    except:
        return previous_summary or ""


def rewrite_query(summary, user_msg):
    prompt = f"""Rewrite the user's question into a standalone query for retrieval.
Use conversation_summary to resolve pronouns and include names/dates/scope.
Return only the rewritten query.

conversation_summary:
{summary or ''}

user_question:
{user_msg}
"""
    try:
        return call_chat([{
            "role":
            "system",
            "content":
            "You turn follow-up questions into standalone queries. Return only the query."
        }, {
            "role": "user",
            "content": prompt
        }],
                         max_tokens=120)
    except:
        return user_msg


def retrieve_for_chat(query, k=20):
    if not chroma_collection:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    try:
        return chroma_collection.query(
            query_texts=[query],
            n_results=k,
            include=["documents", "metadatas", "distances"])
    except:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}


def rerank(query, hits, topn=5):
    # Optional: apply a cross-encoder or heuristic MMR
    # For now, simple diversity by section + distance score
    docs = hits["documents"][0]
    metas = hits["metadatas"][0]
    dists = hits["distances"][0]
    triples = list(zip(docs, metas, dists))
    # naive: sort by distance then pick diverse sections
    triples.sort(key=lambda x: x[2])
    seen = set()
    out = []
    for t in triples:
        sec = t[1].get("section") if t[1] else None
        if sec in seen: continue
        seen.add(sec)
        out.append(t)
        if len(out) >= topn: break
    return out


def build_context(snippets):
    parts = []
    for doc, meta, dist in snippets:
        title = meta.get("title", "") if meta else ""
        parts.append(f"[{title}] {doc}")
    return "\n\n".join(parts[:3])


def need_contact(session):
    """Check if we need contact info (name and phone) from the user."""
    has_name = session.get("name")
    has_phone = session.get("phone") 
    return not (has_name and has_phone)

def get_missing_info(session):
    """Get list of missing information needed from user."""
    missing = []
    
    if not session.get("name"):
        missing.append("name")
    if not session.get("phone"):
        missing.append("phone number")
    if not session.get("location"):
        missing.append("location")
    if not session.get("style_preference"):
        missing.append("style preference")
    
    return missing

def is_conversation_complete(session):
    """Check if we have all required information to complete the conversation."""
    required = ["name", "phone", "location", "style_preference"]
    return all(session.get(field) for field in required)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    hits = search(req.question, top_k=req.top_k or 6)
    if not hits:
        return AskResponse(
            answer="I don't have that information in my knowledge base.",
            sources=[])

    # Load system prompt based on tone type
    system_prompt = load_system_prompt(req.tone_type or "customer_support")

    # Compose context
    sources = []
    ctx_lines = []
    for h in hits:
        url = h["meta"]["url"]
        title = h["meta"]["title"]
        text = h["text"]
        ctx_lines.append(f"[{title}] {text}\n(Source: {url})\n")
        sources.append(url)

    user = f"Question: {req.question}\n\nContext:\n" + "\n".join(ctx_lines[:6])
    msg = [{
        "role": "system",
        "content": system_prompt
    }, {
        "role": "user",
        "content": user
    }]
    answer = call_chat(msg)
    return AskResponse(answer=answer, sources=list(dict.fromkeys(sources)))


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Enhanced chat endpoint with conversation memory and Malaysian business tone."""
    
    st = CHAT_SESSIONS.setdefault(req.thread_id, {
        "summary": "",
        "turns": [],
        "first_turn": True
    })
    first_turn = st["first_turn"]
    user_text = req.user_message

    # Extract and store all information from every message
    try:
        name, name_score = extract_name(user_text)  # Now returns tuple
    except (ValueError, TypeError):
        name, name_score = "", 0
    phone = extract_phone(user_text)
    location = extract_location(user_text)
    
    # Store extracted information - only if we don't already have it
    if name and not st.get("name"):
        st["name"] = name
    if phone and not st.get("phone"):
        st["phone"] = phone
    if location and not st.get("location"):
        st["location"] = location
    
    # Check for style preference using advanced parser
    from utils.parser_my_style_location import extract_style
    
    if not st.get("style_preference"):
        style_result = extract_style(user_text)
        if style_result and style_result.get("theme") != "generic":
            st["style_preference"] = user_text
            # Store theme and portfolio link for later use
            st["style_theme"] = style_result.get("theme")
            st["style_link"] = style_result.get("link", "")


    # Save to database when we have both name and phone
    if st.get("name") and st.get("phone"):
        try:
            # Get the first message from conversation history
            first_msg = st.get("turns")[0][1] if st.get("turns") and len(
                st.get("turns")) > 0 else user_text
            # Determine theme interest from conversation
            theme_interest = ""
            for turn in st.get("turns", []):
                if mentions_theme(turn[1]) and turn[0] == "user":
                    theme_interest = turn[1]
                    break

            save_lead(name=st["name"],
                      phone=st["phone"],
                      thread_id=req.thread_id,
                      location=st.get("location", ""),
                      style_preference=st.get("style_preference", ""))
            print(
                f"✅ SAVED LEAD: {st['name']} - {st['phone']} - Thread: {req.thread_id}"
            )
        except Exception as e:
            print(f"Error saving lead: {e}")

    # Dynamic conversation flow - only end when we have ALL required info
    if is_conversation_complete(st):
        final_name = st.get("name", "there")
        reply = f"Perfect! Thank you {final_name}. I have all the details I need - your contact info, location ({st.get('location')}), and style preference. I'll prepare a proposal and contact you soon at {st.get('phone')}."
        st["conversation_complete"] = True
        st["turns"].append(("user", req.user_message))
        st["turns"].append(("assistant", reply))
        st["summary"] = summarise(st["summary"], req.user_message, reply)
        st["first_turn"] = False
        return ChatResponse(answer=reply, sources=[])
    
    # Progressive information collection - ask for next missing piece
    missing_info = get_missing_info(st)
    if missing_info and (is_lead_only(user_text) or (name and phone) or st.get("name") or st.get("phone")):
        next_question = ""
        if "location" in missing_info:
            next_question = "Great! What's the location of your property? (e.g., Bangsar, Mont Kiara, PJ)"
        elif "style preference" in missing_info:
            next_question = "What kind of style or vibe do you want for your space?"
        elif "name" in missing_info:
            next_question = "May I have your name?"
        elif "phone number" in missing_info:
            next_question = "May I have your phone number so I can follow up?"
            
        if next_question:
            user_name = st.get("name", "")
            if user_name:
                reply = f"Thank you {user_name}! {next_question}"
            else:
                reply = next_question
                
            st["turns"].append(("user", req.user_message))
            st["turns"].append(("assistant", reply))
            st["summary"] = summarise(st["summary"], req.user_message, reply)
            st["first_turn"] = False
            return ChatResponse(answer=reply, sources=[])

    # Greeting handling with tone system
    if is_greeting(req.user_message):

        system_prompt = load_system_prompt("customer_support")
        
        # Create simple greeting context
        greeting_msg = [{
            "role": "system", 
            "content": system_prompt
        }, {
            "role": "user", 
            "content": f"Customer says: {req.user_message}. This is a {'first' if first_turn else 'repeated'} greeting."
        }]
        
        try:
            reply = call_chat(greeting_msg, temperature=0.3, max_tokens=80)
            reply = postprocess(reply, first_turn=first_turn)
        except Exception:
            reply = f"Hi there, this is {req.name} here from {req.company}. How may I help you today?"
        
        st["turns"].append(("user", req.user_message))
        st["turns"].append(("assistant", reply))
        st["summary"] = summarise(st["summary"], req.user_message, reply)
        st["first_turn"] = False
        return ChatResponse(answer=reply, sources=[])

    # Theme detection with contact handling
    if mentions_theme(req.user_message):
        url = resolve_theme_url(req.user_message)
        if url:

            if need_contact(st):
                reply = f"Sure, here's the project we did before {url}. May I have your name and phone number so I can follow up properly?"
            else:
                reply = f"Sure—here's one project that fits: {url}"
        else:
            reply = "We definitely can do that, let's talk more when we meet. Can you provide me your name and phone number?"

        st["turns"].append(("user", req.user_message))
        st["turns"].append(("assistant", reply))
        st["summary"] = summarise(st["summary"], req.user_message, reply)
        st["first_turn"] = False
        return ChatResponse(answer=reply, sources=[])

    # 1) Detect style/feel intent and find theme URL
    theme_url = ""
    if mentions_theme(req.user_message):
        theme_url = resolve_theme_url(req.user_message)

    # Query rewrite -> retrieval -> context
    rewritten = rewrite_query(st["summary"], req.user_message)
    hits = retrieve_for_chat(rewritten)
    top = rerank(rewritten, hits, topn=5)
    context = build_context(top)

    # Build messages
    system_prompt = load_system_prompt("customer_support")
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "system",
            "content": f"THEME_URL: {theme_url}"
        },
        {
            "role": "system",
            "content": f"Conversation summary:\n{st['summary'][:2000]}"
        },
        {
            "role": "system",
            "content": f"Relevant context (snippets):\n{context}"
        },
    ]
    # Add short history (last 2 turns)
    for role, content in st["turns"][-4:]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": req.user_message})

    try:
        raw = call_chat(messages, temperature=0.3, max_tokens=160)
        reply = postprocess(raw, first_turn=False)
    except Exception as e:
        reply = "I'm having trouble responding right now. Could you please try again?"

    # Auto-append portfolio for "why choose" intent
    if re.search(r'\bwhy\b.*\bchoose\b', req.user_message,
                 re.I) and req.portfolio_url and "Portfolio" not in reply:
        reply = f"{reply} Portfolio: {req.portfolio_url}"

    # Update memory
    st["turns"].append(("user", req.user_message))
    st["turns"].append(("assistant", reply))
    st["summary"] = summarise(st["summary"], req.user_message, reply)
    st["first_turn"] = False

    # Optional: include source URLs back
    sources = []
    for _, meta, _ in top:
        if meta and "url" in meta: sources.append(meta["url"])
    return ChatResponse(answer=reply, sources=sources[:3])


@app.post("/crawl", response_model=CrawlResponse)
async def crawl(request: CrawlRequest):
    """Crawl a website and index its content."""
    try:
        # Crawl the website
        client = FirecrawlClient()
        pages_data = client.crawl_website(
            url=str(request.target_url),
            max_pages=request.max_pages,
            include_subdomains=request.include_subdomains)

        if not pages_data:
            raise HTTPException(
                status_code=400,
                detail="Failed to crawl any pages from the website")

        # Process and index the content
        chunk_processor = TextChunker(chunk_size=1000, chunk_overlap=200)
        total_chunks = 0

        for page_data in pages_data:
            try:
                # Process page content into chunks
                chunks = chunk_processor.process_page_content(page_data)

                if chunks:
                    # Convert to the format expected by upsert_chunks
                    chunk_data = []
                    for i, chunk in enumerate(chunks):
                        chunk_data.append({
                            "text":
                            chunk['content'],
                            "url":
                            chunk['metadata'].get('url', ''),
                            "title":
                            chunk['metadata'].get('title', 'Untitled'),
                            "chunk_idx":
                            i,
                            "scraped_at":
                            str(time.time())
                        })

                    # Index the chunks
                    upsert_chunks(chunk_data)
                    total_chunks += len(chunk_data)
            except Exception as e:
                print(
                    f"Failed to index page {page_data.get('url', 'unknown')}: {str(e)}"
                )
                continue

        return CrawlResponse(
            success=True,
            pages_crawled=len(pages_data),
            chunks_indexed=total_chunks,
            message=
            f"Successfully crawled {len(pages_data)} pages and indexed {total_chunks} content chunks!"
        )

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Failed to crawl website: {str(e)}")


@app.get("/crawled-pages")
async def get_crawled_pages():
    """Get list of crawled pages with statistics."""
    try:
        from app.indexer import collection

        # Get all documents with metadata
        results = collection.get(include=['metadatas'])

        if not results['metadatas']:
            return []

        # Group by URL and collect statistics
        url_data = {}
        for metadata in results['metadatas']:
            url = metadata.get('url', 'Unknown')
            if url != 'Unknown':
                if url not in url_data:
                    url_data[url] = {
                        'count': 0,
                        'title': metadata.get('title', 'Untitled'),
                        'last_crawled': None
                    }
                url_data[url]['count'] += 1

                # Get the latest scraped time
                scraped_at = metadata.get('scraped_at')
                if scraped_at:
                    try:
                        scraped_timestamp = float(scraped_at)
                        if not url_data[url][
                                'last_crawled'] or scraped_timestamp > url_data[
                                    url]['last_crawled']:
                            url_data[url]['last_crawled'] = scraped_timestamp
                    except (ValueError, TypeError):
                        pass

        # Convert to response format
        crawled_pages = []
        for url, data in url_data.items():
            last_crawled = None
            if data['last_crawled']:
                from datetime import datetime
                last_crawled = datetime.fromtimestamp(
                    data['last_crawled']).strftime('%Y-%m-%d %H:%M:%S')

            crawled_pages.append({
                "url": url,
                "title": data['title'],
                "chunks_count": data['count'],
                "last_crawled": last_crawled
            })

        return crawled_pages

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Failed to get crawled pages: {str(e)}")
