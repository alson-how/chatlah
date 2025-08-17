# app/controller.py
import re
from typing import Dict, Tuple
from app.slots import ConversationState, Slot, QUESTIONS
from app.late_capture import parse_all
from app.rag_assist import maybe_answer_with_rag
from app.intents import is_portfolio_intent
from app.portfolio_preview import portfolio_preview
from utils.theme import resolve_theme_url, mentions_theme

PORTFOLIO_URL = "https://jablancinteriors.com/projects/"
REASK_PREFIX = "Just to confirm,"

def _next_followup_question(state: ConversationState) -> str | None:
    # After answering their request, continue the funnel in this priority
    if not state.style:    return QUESTIONS[Slot.STYLE]
    if not state.location: return QUESTIONS[Slot.LOCATION]
    if not state.phone:    return QUESTIONS[Slot.PHONE]
    return None

def craft_reply(user_text: str, state: ConversationState) -> Tuple[str, ConversationState]:
    # 1) Late capture any fields given this turn
    parsed = parse_all(user_text)
    if parsed["name"] and not state.name:         state.name = parsed["name"]
    if parsed["phone"] and not state.phone:       state.phone = parsed["phone"]
    if parsed["style"] and not state.style:       state.style = parsed["style"]
    if parsed["location"] and not state.location: state.location = parsed["location"]

    # 2) HIGH-PRIORITY INTENT: Portfolio
    if is_portfolio_intent(user_text):
        # Always answer first
        preview = portfolio_preview()  # may return None
        head = f"Yes sure, you may look at our portfolio here {PORTFOLIO_URL}."
        body = f"\n{preview}" if preview else ""
        follow = _next_followup_question(state)
        tail = f"\n{follow}" if follow else ""
        return (head + body + tail).strip(), state

    # 3) Normal flow continues below -------------
    slot = state.next_slot()

    # If user shows generic ID intent but we still need style, probe style
    generic_id_intent = bool(re.search(r"\b(id|interior design|renovation|makeover|concept)\b", user_text, re.I))
    if slot in (Slot.NAME, Slot.PHONE) and generic_id_intent and not state.style:
        rag_line = maybe_answer_with_rag(user_text) or None
        style_probe = "What kind of style or vibe you want?"
        if rag_line:
            return f"{rag_line}\n{style_probe}", state
        return style_probe, state

    # If current slot was answered this turn, store and advance
    if slot == Slot.NAME and parsed["name"]:
        state.name = parsed["name"]
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.PHONE and parsed["phone"]:
        state.phone = parsed["phone"]
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.STYLE and (mentions_theme(user_text) or parsed["style"]):
        state.style = parsed["style"] or "theme_detected"
        link = resolve_theme_url(user_text)
        if link:
            return f"Sure—here’s one project that fits: {link}\n{QUESTIONS[state.next_slot()]}", state
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.LOCATION and parsed["location"]:
        state.location = parsed["location"]
        return QUESTIONS[state.next_slot()], state

    if slot == Slot.SCOPE:
        if re.search(r"\b(living|kitchen|bed(room)?|dining|study|office|retail|toilet|bath)\b", user_text, re.I):
            state.scope = user_text
            return "Thanks. Would you like a quick consult or a rough estimate?", state

    # Off-topic? Give short RAG, then re-ask pending slot
    rag_line = maybe_answer_with_rag(user_text)
    hint = ""
    if slot == Slot.STYLE:    hint = " For example, modern minimalist, warm neutral, or industrial."
    if slot == Slot.LOCATION: hint = " For example, Mont Kiara, Bangsar, or Penang."
    if slot == Slot.SCOPE:    hint = " For example, living and kitchen."
    question = QUESTIONS[slot] + hint

    # Lead-capture ask-once (only if we truly need it and not after a portfolio intent)
    if slot in (Slot.NAME, Slot.PHONE) and not state.asked_name_phone_once and not is_portfolio_intent(user_text):
        state.asked_name_phone_once = True
        return "May I have your name and phone number so I can follow up properly?", state

    if rag_line:
        return f"{rag_line}\n{REASK_PREFIX} {question}", state

    return question, state
