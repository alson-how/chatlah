"""
Slot management for conversational AI.
Handles conversation state, slot progression, and question generation.
"""

from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Optional, Dict, List
import random

class Slot(Enum):
    NAME = auto()
    PHONE = auto()
    STYLE = auto()
    LOCATION = auto()
    SCOPE = auto()
    NONE = auto()

# Standard slot questions
QUESTIONS: Dict[Slot, str] = {
    Slot.NAME:     "May I have your name?",
    Slot.PHONE:    "What's the best phone number to reach you?",
    Slot.STYLE:    "What kind of style or vibe you want?",
    Slot.LOCATION: "Which area is the property located?",
    Slot.SCOPE:    "Which spaces are in scope? For example, living, kitchen, master bedroom."
}

# Phone ask prompts with variations
PHONE_PROMPTS = [
    "What's the best phone number to reach you?",
    "Could you share a contact number so I can follow up properly?",
    "Mind sharing your phone number? I'll WhatsApp you the next steps.",
]

# Appointment scheduling messages
APPOINTMENT_MESSAGES = [
    "Perfect! I have your details - {name}, {phone}, {style} style in {location}.",
    "Let me schedule a consultation for you. When would be a good time this week?",
    "I can arrange a site visit - would morning or afternoon work better?",
    "Our designer will contact you within 24 hours to arrange a meeting.",
    "Would you prefer a weekday or weekend appointment for the consultation?"
]

@dataclass
class ConversationState:
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
        """Determine the next slot that needs to be filled."""
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

def get_dynamic_field_configs() -> List[Dict]:
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

def dynamic_next_slot(state: ConversationState) -> Optional[str]:
    """Get next missing required field based on admin configuration."""
    field_configs = get_dynamic_field_configs()
    required_fields = [f for f in field_configs if f['is_required']]
    required_fields.sort(key=lambda x: x['sort_order'])
    
    for field_config in required_fields:
        field_name = field_config['field_name']
        if not getattr(state, field_name, None):
            return field_config['question_text']
    
    return None

def is_ready_for_appointment_dynamic(state: ConversationState) -> bool:
    """Check if all required fields are collected based on admin configuration."""
    field_configs = get_dynamic_field_configs()
    required_fields = [f for f in field_configs if f['is_required']]
    
    for field_config in required_fields:
        field_name = field_config['field_name']
        if not getattr(state, field_name, None):
            return False
    
    return True

def next_phone_prompt(state: ConversationState) -> Optional[str]:
    """Get next phone prompt with cooldown and rotation."""
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

def mark_phone_prompted(state: ConversationState):
    """Mark that phone was prompted in this turn."""
    state.asked_phone_count += 1
    state.last_phone_prompt_turn = state.turn_index

def next_missing_after_portfolio(state: ConversationState) -> Optional[str]:
    """Get next missing field question after portfolio interaction."""
    if not state.style:    return QUESTIONS[Slot.STYLE]
    if not state.location: return QUESTIONS[Slot.LOCATION]
    if not state.phone:    return QUESTIONS[Slot.PHONE]
    return None

def next_non_phone_slot_question(state: ConversationState) -> Optional[str]:
    """Get next non-phone field question for conversation flow."""
    if not state.style:    return QUESTIONS[Slot.STYLE]
    if not state.location: return QUESTIONS[Slot.LOCATION]
    if not state.scope:    return QUESTIONS[Slot.SCOPE]
    return None

def generate_appointment_message(state: ConversationState) -> str:
    """Generate appointment scheduling message with user details."""
    appointment_msg = random.choice(APPOINTMENT_MESSAGES)
    return appointment_msg.format(
        name=state.name or 'there',
        phone=state.phone or 'your contact',
        style=getattr(state, 'style', 'your preferred style') or 'your preferred style',
        location=getattr(state, 'location', 'your location') or 'your location'
    )

def get_slot_question_with_hints(slot: Slot) -> str:
    """Get slot question with helpful hints."""
    question = QUESTIONS[slot]
    hint = ""
    
    if slot == Slot.STYLE:    
        hint = " For example, modern minimalist, warm neutral, or industrial."
    elif slot == Slot.LOCATION: 
        hint = " For example, Mont Kiara, Bangsar, or Penang."
    elif slot == Slot.SCOPE:    
        hint = " For example, living and kitchen."
    
    return question + hint