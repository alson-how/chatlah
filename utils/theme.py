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
        return {}

_theme_map = _load_theme_map()

def _normalize(text: str) -> str:
    """Normalize text for theme matching."""
    return re.sub(r'[^a-z0-9\s-]+', ' ', text.lower()).strip()

def mentions_theme(text: str) -> bool:
    """Check if the text mentions theme-related keywords."""
    print(f"MENTIONS_THEME called with: '{text}'")
    t = _normalize(text)
    print(f"MENTIONS_THEME normalized: '{t}'")
    result = any(k in t for k in THEME_KEYS)
    print(f"MENTIONS_THEME result: {result}")
    return result

def resolve_theme_url(text: str) -> str:
    """Return best matching theme URL or empty string if no good match."""
    print(f"RESOLVE_THEME_URL called with: '{text}'")
    if not _theme_map:
        print("No theme map loaded!")
        return ""
        
    t = _normalize(text)
    print(f"RESOLVE_THEME_URL normalized: '{t}'")
    
    # 1) exact/substring match
    for key, url in _theme_map.items():
        if key in t:
            print(f"Direct match found: '{key}' -> '{url}'")
            return url
        # Also check individual keywords from the key
        key_words = [word.strip() for word in key.split(',')]
        for keyword in key_words:
            if keyword.strip() in t:
                print(f"Keyword match found: '{keyword}' -> '{url}'")
                return url
    
    # 2) fuzzy match (closest key above threshold)
    keys = list(_theme_map.keys())
    best = difflib.get_close_matches(t, keys, n=1, cutoff=0.72)
    if best:
        return _theme_map[best[0]]
    
    # 3) try token-level fuzzy (for phrases like 'modern clean minimal feel')
    tokens = t.split()
    for window in range(min(4, len(tokens)), 0, -1):
        for i in range(len(tokens) - window + 1):
            phrase = " ".join(tokens[i:i + window])
            best = difflib.get_close_matches(phrase, keys, n=1, cutoff=0.85)
            if best:
                return _theme_map[best[0]]
    
    return ""