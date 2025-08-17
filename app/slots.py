# app/slots.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Optional, Dict

class Slot(Enum):
    NAME = auto()
    PHONE = auto()
    STYLE = auto()
    LOCATION = auto()
    SCOPE = auto()
    NONE = auto()

QUESTIONS: Dict[Slot, str] = {
    Slot.NAME:     "May I have your name?",
    Slot.PHONE:    "What’s the best phone number to reach you?",
    Slot.STYLE:    "What kind of style or vibe you want?",
    Slot.LOCATION: "Which area is the property located?",
    Slot.SCOPE:    "Which spaces are in scope? For example, living, kitchen, master bedroom."
}

@dataclass
class ConversationState:
    lead_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    style: Optional[str] = None
    location: Optional[str] = None
    scope: Optional[str] = None
    asked_name_phone_once: bool = False  # enforce “ask once” rule

    def next_slot(self) -> Slot:
        if not self.name:     return Slot.NAME
        if not self.phone:    return Slot.PHONE
        if not self.style:    return Slot.STYLE
        if not self.location: return Slot.LOCATION
        if not self.scope:    return Slot.SCOPE
        return Slot.NONE

    def to_dict(self): return asdict(self)
