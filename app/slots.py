"""
Slot management for conversational AI.
Handles conversation state, slot progression, and question generation.
"""

from dataclasses import dataclass, asdict, field
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
    
    # Checklist tracking for better question rotation
    last_asked_field: Optional[str] = None
    field_ask_counts: Dict[str, int] = field(default_factory=lambda: {"name": 0, "phone": 0, "style": 0, "location": 0, "scope": 0})
    last_field_ask_turn: Dict[str, int] = field(default_factory=lambda: {"name": -1, "phone": -1, "style": -1, "location": -1, "scope": -1})
    
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
    """Get next missing required field with checklist rotation logic."""
    next_question = get_next_checklist_question(state)
    if next_question:
        # Extract field name from question to mark it
        field_configs = get_dynamic_field_configs()
        for field_config in field_configs:
            if field_config['question_text'] == next_question:
                mark_field_asked(state, field_config['field_name'])
                break
    return next_question

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

def get_checklist_progress(state: ConversationState) -> Dict[str, bool]:
    """Get completion status of all checklist items."""
    return {
        "name": bool(state.name),
        "phone": bool(state.phone),
        "style": bool(state.style),
        "location": bool(state.location),
        "scope": bool(state.scope)
    }

def get_missing_required_fields(state: ConversationState) -> List[str]:
    """Get list of missing required fields based on priority order."""
    field_configs = get_dynamic_field_configs()
    required_fields = [f for f in field_configs if f['is_required']]
    required_fields.sort(key=lambda x: x['sort_order'])
    
    missing = []
    for field_config in required_fields:
        field_name = field_config['field_name']
        if not getattr(state, field_name, None):
            missing.append(field_name)
    
    return missing

def get_next_checklist_question(state: ConversationState, cooldown_turns: int = 2) -> Optional[str]:
    """Get next question with intelligent rotation and cooldown."""
    # Get missing required fields
    missing_fields = get_missing_required_fields(state)
    if not missing_fields:
        return None
    
    # Apply cooldown - don't ask same field within cooldown period
    available_fields = []
    for field in missing_fields:
        last_ask_turn = state.last_field_ask_turn.get(field, -1)
        if (state.turn_index - last_ask_turn) >= cooldown_turns:
            available_fields.append(field)
    
    # If no fields available due to cooldown, pick the oldest asked
    if not available_fields:
        oldest_field = min(missing_fields, 
                          key=lambda f: state.last_field_ask_turn.get(f, -1))
        available_fields = [oldest_field]
    
    # Rotate questions - don't ask same field twice in a row
    if state.last_asked_field in available_fields and len(available_fields) > 1:
        available_fields = [f for f in available_fields if f != state.last_asked_field]
    
    # Pick the field with lowest ask count, or first available
    next_field = min(available_fields, 
                    key=lambda f: state.field_ask_counts.get(f, 0))
    
    # Get the question text for this field
    field_configs = get_dynamic_field_configs()
    for field_config in field_configs:
        if field_config['field_name'] == next_field:
            return field_config['question_text']
    
    # Fallback to standard questions
    slot_map = {
        'name': Slot.NAME, 
        'phone': Slot.PHONE, 
        'style': Slot.STYLE, 
        'location': Slot.LOCATION, 
        'scope': Slot.SCOPE
    }
    return QUESTIONS.get(slot_map.get(next_field))

def mark_field_asked(state: ConversationState, field_name: str):
    """Mark that a field was asked in this turn."""
    state.last_asked_field = field_name
    state.field_ask_counts[field_name] = state.field_ask_counts.get(field_name, 0) + 1
    state.last_field_ask_turn[field_name] = state.turn_index

def next_missing_after_portfolio(state: ConversationState) -> Optional[str]:
    """Get next missing field question after portfolio interaction with proper rotation."""
    next_question = get_next_checklist_question(state)
    if next_question:
        # Extract field name from question to mark it
        field_configs = get_dynamic_field_configs()
        for field_config in field_configs:
            if field_config['question_text'] == next_question:
                mark_field_asked(state, field_config['field_name'])
                break
    return next_question

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