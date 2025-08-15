# utils/lead.py
import re

def extract_name(text: str) -> str:
    """Extract name from user message."""
    text = text.lower().strip()
    
    # Pattern: "my name is [name]" or "i'm [name]" or "i am [name]"
    patterns = [
        r"my name is ([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",  # Stop at first 1-2 words
        r"i'?m ([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
        r"i am ([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
        r"name is ([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
        r"call me ([a-zA-Z]+(?:\s+[a-zA-Z]+)?)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip().title()
            # Filter out common words that aren't names
            if name.lower() not in ['interested', 'looking', 'here', 'ready', 'good', 'fine', 'okay', 'and', 'my', 'phone', 'is', 'looking for', 'interested in', 'planning to', 'hoping to', 'wanting to', 'trying to']:
                # Stop at common connector words
                words = name.split()
                clean_words = []
                for word in words:
                    if word.lower() in ['and', 'my', 'phone', 'is', 'number', 'please', 'call', 'contact', 'at']:
                        break
                    clean_words.append(word)
                if clean_words:
                    return ' '.join(clean_words)
    
    return ""

def extract_phone(text: str) -> str:
    """Extract phone number from user message."""
    # Malaysian phone number patterns
    patterns = [
        r'(\+?6?01[0-9]{8,9})',  # Malaysian mobile
        r'(\+?6?03[0-9]{8})',     # KL landline
        r'(\+?6?0[4-9][0-9]{7,8})', # Other Malaysian numbers
        r'([0-9]{10,11})',        # Generic 10-11 digit numbers
        r'([0-9]{3}[-\s]?[0-9]{3}[-\s]?[0-9]{4})', # Formatted numbers
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r'[-\s]', '', match.group(1))
            # Basic validation - must be 10-12 digits
            if 10 <= len(phone) <= 12:
                return phone
    
    return ""

def is_lead_only(text: str) -> bool:
    """Check if message is only providing contact info without other questions."""
    text = text.lower().strip()
    
    # If it contains name or phone patterns but no other meaningful content
    has_name = bool(extract_name(text))
    has_phone = bool(extract_phone(text))
    
    if not (has_name or has_phone):
        return False
    
    # Remove contact info and see what's left
    temp = text
    for pattern in [
        r"my name is [a-zA-Z\s]+",
        r"i'?m [a-zA-Z\s]+", 
        r"i am [a-zA-Z\s]+",
        r"name is [a-zA-Z\s]+",
        r"call me [a-zA-Z\s]+",
        r"\+?6?0[0-9]{8,11}",
        r"[0-9]{10,12}",
        r"[0-9]{3}[-\s]?[0-9]{3}[-\s]?[0-9]{4}",
        r"phone", r"number", r"contact", r"reach"
    ]:
        temp = re.sub(pattern, '', temp)
    
    # If less than 5 meaningful characters left, it's likely lead-only
    meaningful_chars = re.sub(r'[^a-zA-Z]', '', temp)
    return len(meaningful_chars) < 5