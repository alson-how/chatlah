# app/controller.py
import re
from typing import Dict, Tuple
from app.slots import ConversationState, Slot, QUESTIONS
from app.late_capture import parse_all
from app.rag_assist import maybe_answer_with_rag
from utils.theme import resolve_theme_url, mentions_theme
from utils.lead import is_lead_only, extract_name, extract_phone  
from utils.location import mentions_location_need, extract_location

REASK_PREFIX = "Just to confirm,"

def craft_reply(user_text: str, state: ConversationState) -> Tuple[str, ConversationState]:
    # 1) Late capture anything the user provided (name/phone/style/location)
    parsed = parse_all(user_text)
    if parsed["name"] and not state.name:       state.name = parsed["name"]
    if parsed["phone"] and not state.phone:     state.phone = parsed["phone"]
    if parsed["style"] and not state.style:     state.style = parsed["style"]
    if parsed["location"] and not state.location: state.location = parsed["location"]

    # 2) Decide what to ask next
    slot = state.next_slot()

    # Special routing: If user expressed generic ID intent without style → probe style first
    generic_id_intent = bool(re.search(r"\b(id|interior design|renovation|makeover|concept)\b", user_text, re.I))
    if slot in (Slot.NAME, Slot.PHONE) and generic_id_intent and not state.style:
        # keep the flow friendly; do not re-ask name/phone immediately
        rag_line = maybe_answer_with_rag(user_text) or None
        style_probe = "What kind of style or vibe you want?"
        if rag_line:
            return f"{rag_line}\n{style_probe}", state
        return style_probe, state

    # 3) If user actually answered the current slot this turn, store and advance
    if slot == Slot.NAME and parsed["name"]:
        state.name = parsed["name"]
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.PHONE and parsed["phone"]:
        state.phone = parsed["phone"]
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.STYLE and (mentions_theme(user_text) or parsed["style"]):
        state.style = parsed["style"] or "theme_detected"
        # Optional: send one matching project link if you have a mapping
        link = resolve_theme_url(user_text)  # you already have this util
        if link:
            return f"Sure—here’s one project that fits: {link}\n{QUESTIONS[state.next_slot()]}", state
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.LOCATION and parsed["location"]:
        state.location = parsed["location"]
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.SCOPE:
        # treat any mention of rooms as scope
        if re.search(r"\b(living|kitchen|bed(room)?|dining|study|office|retail|toilet|bath)\b", user_text, re.I):
            state.scope = user_text
            return "Thanks. Would you like a quick consult or a rough estimate?", state

    # 4) If user went off-topic, give a short factual RAG line, then re-ask the pending slot
    rag_line = maybe_answer_with_rag(user_text)
    hint = ""
    if slot == Slot.STYLE:    hint = " For example, modern minimalist, warm neutral, or industrial."
    if slot == Slot.LOCATION: hint = " For example, Mont Kiara, Bangsar, or Penang."
    if slot == Slot.SCOPE:    hint = " For example, living and kitchen."

    question = QUESTIONS[slot] + hint
    if rag_line:
        return f"{rag_line}\n{REASK_PREFIX} {question}", state

    # 5) Initial lead capture ask-once rule
    if slot in (Slot.NAME, Slot.PHONE) and not state.asked_name_phone_once:
        state.asked_name_phone_once = True
        # Combine in one line to reduce friction on WhatsApp
        return "May I have your name and phone number so I can follow up properly?", state

    # 6) Otherwise, just re-ask the pending slot
    return question, state
