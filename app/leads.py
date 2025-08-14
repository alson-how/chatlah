# utils/lead.py
import re

PHONE_RE = re.compile(r"(?:\+?60[-\s]?)?0?1\d(?:[-\s]?\d){7,8}")  # MY mobile-ish
NAME_HINTS_RE = re.compile(r"\b(my name is|this is|i am|i'm)\b", re.I)

def normalize_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw)
    # To E.164 (MY): +60XXXXXXXXX
    if digits.startswith("+60"):
        return digits
    if digits.startswith("60"):
        return "+" + digits
    if digits.startswith("0"):  # local format e.g. 01XXXXXXXX
        return "+60" + digits[1:]
    # Fallback: assume already ok
    return digits

def extract_phone(text: str) -> str | None:
    m = PHONE_RE.search(text)
    return normalize_phone(m.group(0)) if m else None

def extract_name(text: str) -> str | None:
    # Try "my name is / this is / I'm Ali ..." patterns
    m = re.search(r"(?:my name is|this is|i am|i'm)\s+([A-Za-z][A-Za-z' .-]{1,40})", text, re.I)
    if m:
        return m.group(1).strip(" .-")
    # If comma-separated "Ali, 0123..."
    if "," in text:
        left = text.split(",", 1)[0].strip()
        if 1 <= len(left.split()) <= 4 and left and left[0].isalpha():
            return left
    # If first token(s) look like a name and there's a phone in message
    if extract_phone(text):
        # take leading words before phone
        phone = extract_phone(text)
        lead = text.split(phone or "", 1)[0]
        cand = re.sub(r"[^A-Za-z' .-]", " ", lead).strip()
        words = [w for w in cand.split() if w]
        if 1 <= len(words) <= 4:
            return " ".join(words)
    return None

def is_lead_only(text: str) -> bool:
    # Lead-only = contains phone OR name hints, and no question marks, and few words
    t = text.strip()
    if "?" in t:
        return False
    has_phone = extract_phone(t) is not None
    has_name_hint = bool(NAME_HINTS_RE.search(t)) or ("," in t)
    word_count = len(re.findall(r"\w+", t))
    return (has_phone or has_name_hint) and word_count <= 10
