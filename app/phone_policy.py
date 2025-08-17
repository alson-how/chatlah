# phone_policy.py
from typing import Optional

PHONE_PROMPTS = [
    "What’s the best phone number to reach you?",
    "Could you share a contact number so I can follow up properly?",
    "Mind sharing your phone number? I’ll WhatsApp you the next steps.",
]

def next_phone_prompt(state) -> Optional[str]:
    # Cooldown: don’t repeat within 2 turns
    if state.asked_phone_count > 0 and (state.turn_index - state.last_phone_prompt_turn) < 2:
        return None
    # Stop after 3 attempts; we’ll keep progressing other slots
    if state.asked_phone_count >= 3:
        return None
    variant = PHONE_PROMPTS[state.asked_phone_count % len(PHONE_PROMPTS)]
    if state.name:
        variant = f"Thanks, {state.name}. {variant}"
    return variant

def mark_phone_prompted(state):
    state.asked_phone_count += 1
    state.last_phone_prompt_turn = state.turn_index
