# utils/theme.py
import json
import re
import difflib
from pathlib import Path

THEME_KEYS = [
    "style", "theme", "feel", "vibe", "look", "aesthetic", "direction", 
    "minimalist", "modern", "contemporary", "industrial", "natural", 
    "warm", "clean", "elegant", "functional", "luxury", "cozy", "bright"
]

def _load_theme_map():
    """Load the theme mapping from JSON file."""
    try:
        return json.loads(Path("theme_map.json").read_text())
    except FileNotFoundError:
        return []

_theme_map = _load_theme_map()

def _normalize(text: str) -> str:
    """Normalize text for theme matching."""
    return re.sub(r'[^a-z0-9\s-]+', ' ', text.lower()).strip()

def mentions_theme(text: str) -> bool:
    """Check if the text mentions theme-related keywords."""
    t = _normalize(text)
    return any(k in t for k in THEME_KEYS)

def resolve_theme_url(text: str) -> str:
    """Return best matching theme URL or empty string if no good match."""
    if not _theme_map:
        return ""
        
    t = _normalize(text)
    
    # 1) exact/substring match
    for item in _theme_map:
        keyword = item["keyword"]
        url = item["url"]
        if keyword in t:
            return url
        # Also check individual keywords from the keyword field
        key_words = [word.strip() for word in keyword.split(',')]
        for kw in key_words:
            if kw.strip() in t:
                return url
    
    # 2) fuzzy match (closest keyword above threshold)
    keywords = [item["keyword"] for item in _theme_map]
    best = difflib.get_close_matches(t, keywords, n=1, cutoff=0.72)
    if best:
        for item in _theme_map:
            if item["keyword"] == best[0]:
                return item["url"]
    
    # 3) try token-level fuzzy (for phrases like 'modern clean minimal feel')
    tokens = t.split()
    for window in range(min(4, len(tokens)), 0, -1):
        for i in range(len(tokens) - window + 1):
            phrase = " ".join(tokens[i:i + window])
            best = difflib.get_close_matches(phrase, keywords, n=1, cutoff=0.85)
            if best:
                for item in _theme_map:
                    if item["keyword"] == best[0]:
                        return item["url"]
    
    return ""