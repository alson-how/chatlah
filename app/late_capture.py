# app/late_capture.py
import re
from typing import Dict, Optional
from utils.lead import extract_name, extract_phone
from utils.location import extract_location
from utils.theme import mentions_theme, resolve_theme_url

def parse_all(user_text: str) -> Dict[str, Optional[str]]:
    """Extract any fields from the message even if not asked right now."""
    try:
        name, name_score = extract_name(user_text)  # Returns tuple now
    except (ValueError, TypeError):
        name, name_score = "", 0
        
    phone = extract_phone(user_text)
    location = extract_location(user_text)
    style = None
    
    if mentions_theme(user_text):
        # Extract style preference from the text
        from utils.parser_my_style_location import extract_style
        style_result = extract_style(user_text)
        if style_result and style_result.get("theme") != "generic":
            style = user_text  # Store the original text as style preference
        else:
            style = "theme_detected"
            
    return {
        "name": name if name and name_score >= 2 else None,
        "phone": phone,
        "location": location,
        "style": style
    }
