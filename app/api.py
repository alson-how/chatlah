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

# Import modularized components
from app.intents import (
    detect_intent, Intent, is_portfolio_intent, is_generic_id_intent, 
    rag_answer_one_liner, portfolio_preview, respond_with_intent
)
from app.slots import (
    ConversationState, Slot, QUESTIONS, APPOINTMENT_MESSAGES,
    next_phone_prompt, mark_phone_prompted, next_missing_after_portfolio,
    next_non_phone_slot_question, dynamic_next_slot, is_ready_for_appointment_dynamic,
    generate_appointment_message, get_slot_question_with_hints,
    get_checklist_progress, get_missing_required_fields, get_dynamic_field_configs
)

def extract_budget(text: str) -> Optional[str]:
    """Extract budget information from user text."""
    text_lower = text.lower()
    
    # Budget patterns: number + k, number + thousand, rm + number, etc.
    budget_patterns = [
        r'\b(\d+[,.]?\d*)\s*k\b',  # 50k, 100k
        r'\b(\d+[,.]?\d*)\s*thousand\b',  # 50 thousand
        r'\brm\s*(\d+[,.]?\d*)\s*k?\b',  # rm 50k, rm 100
        r'\b(\d+[,.]?\d*)\s*budget\b',  # 50k budget
        r'\ballocated?\s*(\d+[,.]?\d*)\s*k?\b',  # allocated 50k
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, text_lower)
        if match:
            amount = match.group(1)
            # Return in a consistent format
            try:
                num = float(amount.replace(',', ''))
                if num >= 1000:
                    return f"{int(num/1000)}k"
                else:
                    return f"{int(num)}k"
            except ValueError:
                return amount + "k"
    
    return None

# Enhanced late capture function
def enhanced_late_capture(user_text: str, state: ConversationState) -> None:
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
    
    # Budget extraction
    if not state.budget:
        budget = extract_budget(user_text)
        if budget:
            state.budget = budget

# Core enhanced controller
REASK_PREFIX = "Just to confirm,"

def enhanced_handle_turn(user_text: str, state: ConversationState) -> str:
    """Enhanced slot-driven conversation handler with RAG integration and appointment scheduling."""
    state.turn_index += 1

    # 1) Late-capture anything provided this turn
    enhanced_late_capture(user_text, state)

    # 2) Check if ready for appointment after capture using dynamic config
    if is_ready_for_appointment_dynamic(state):
        return generate_appointment_message(state)

    # 3) Intent-first response with built-in follow-up
    intent = detect_intent(user_text)
    intent_reply = respond_with_intent(intent, user_text, state, PORTFOLIO_URL)
    if intent_reply:
        return intent_reply

    # 4) Determine current slot
    slot = state.next_slot()

    # 5) If user expressed generic ID intent but we're still missing style, probe style first
    if slot in (Slot.NAME, Slot.PHONE) and is_generic_id_intent(user_text) and not state.style:
        rag_line = rag_answer_one_liner(user_text) or ""
        style_probe = QUESTIONS[Slot.STYLE]
        return (rag_line + ("\n" if rag_line else "") + style_probe).strip()

    # 6) Check if user answered current slot this turn - use dynamic slot checking
    next_question = dynamic_next_slot(state)
    if not next_question:
        # Check for appointment readiness after slot progression
        if is_ready_for_appointment_dynamic(state):
            return generate_appointment_message(state)
        
        # Optional: if style was just captured, send matching project link
        if hasattr(state, 'style') and state.style and mentions_theme(user_text):
            link = resolve_theme_url(user_text)
            if link:
                return f"Sure—here's one project that fits: {link}\nWhat else would you like to know?"
        
        return "Thank you for providing all the information! Our team will be in touch soon."
    
    # If there's a next question to ask, return it
    if next_question:
        return next_question

    # 7) Enhanced off-topic handling with smart phone policy
    rag_line = rag_answer_one_liner(user_text)
    question = get_slot_question_with_hints(slot)

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
ENHANCED_SESSIONS: Dict[str, ConversationState] = {}

def get_enhanced_state(user_id: str) -> ConversationState:
    """Get enhanced conversation state for a user."""
    if user_id not in ENHANCED_SESSIONS:
        ENHANCED_SESSIONS[user_id] = ConversationState(user_id=user_id)
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
        "completion_progress": get_checklist_progress(state),
        "missing_fields": get_missing_required_fields(state),
        "checklist_status": {
            "total_required": len([f for f in get_dynamic_field_configs() if f['is_required']]),
            "completed": len([f for f in get_dynamic_field_configs() if f['is_required'] and getattr(state, f['field_name'], None)]),
            "last_asked": state.last_asked_field
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

    # Enhanced intent detection with optimized portfolio handling
    from app.intents import detect_intent, respond_with_intent, Intent
    from app.slots import ConversationState
    
    # Create conversation state from session data
    conv_state = ConversationState(user_id=req.thread_id)
    conv_state.name = st.get("name")
    conv_state.phone = st.get("phone")  
    conv_state.location = st.get("location")
    conv_state.style = st.get("style_theme")
    conv_state.turn_index = len(st.get("turns", [])) + 1
    
    # Detect intent and respond with optimized handlers
    intent = detect_intent(req.user_message)
    if intent != Intent.NONE:
        intent_reply = respond_with_intent(intent, req.user_message, conv_state, req.portfolio_url)
        if intent_reply:
            st["turns"].append(("user", req.user_message))
            st["turns"].append(("assistant", intent_reply))
            st["summary"] = summarise(st["summary"], req.user_message, intent_reply)
            st["first_turn"] = False
            return ChatResponse(answer=intent_reply, sources=[])

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
