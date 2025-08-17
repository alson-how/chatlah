# controller.py (inside your turn handler)
from app.rag_assist import maybe_rag_line
from app.phone_policy import next_phone_prompt, mark_phone_prompted

def handle_turn(user_text: str, state) -> str:
    state.turn_index += 1

    # 0) Late-capture any new info (name/style/location/phone)
    # ... your existing late-capture here ...
    # if phone parsed: save & continue to next slot

    # 1) High-priority intents that deserve immediate answers (e.g., portfolio)
    if is_portfolio_intent(user_text):
        reply = "Yes sure, you may look at our portfolio here https://jablancinteriors.com/projects/."
        # continue funnel after answering
        follow = next_missing_after_portfolio(state)  # e.g., STYLE→LOCATION→PHONE
        return f"{reply}\n{follow}" if follow else reply

    # 2) If phone still missing, don’t loop: answer side-topic briefly via RAG, then ask or defer
    if not state.phone:
        rag_line = maybe_rag_line(user_text)  # None or "1-sentence (Source: …)"
        phone_prompt = next_phone_prompt(state)  # None if cooled down or exceeded attempts

        # If user asked something else, be helpful first
        if rag_line and phone_prompt:
            mark_phone_prompted(state)
            return f"{rag_line}\n{phone_prompt}"

        if rag_line and not phone_prompt:
            # Cooldown active or attempts exhausted: just answer and move the funnel forward
            nxt = next_non_phone_slot_question(state)  # e.g., STYLE or LOCATION
            return f"{rag_line}\n{nxt}" if nxt else rag_line

        if (not rag_line) and phone_prompt:
            # No side-topic detected, we can ask for phone once (or rotated)
            mark_phone_prompted(state)
            return phone_prompt

        # Neither rag_line nor phone_prompt (cooldown): progress other slots instead
        nxt = next_non_phone_slot_question(state)
        if nxt:
            return nxt

    # 3) Handle other slots normally (style/location/scope), with your existing logic
    # ...
    return fallback_or_thanks()
