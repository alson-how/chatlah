# app/theme_router.py
import json, re, difflib
from pathlib import Path

THEME_KEYS = [
    "style", "theme", "feel", "vibe", "look", "aesthetic", "direction"
]

_map = json.loads(Path("theme_map.json").read_text())


def _normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9\s-]+', ' ', text.lower()).strip()


def detect_theme_query(text: str) -> bool:
    t = _normalize(text)
    return any(k in t for k in THEME_KEYS)


def find_theme_url(text: str) -> str:
    """Return best URL or '' if no good match."""
    t = _normalize(text)
    # 1) exact/substring match
    for key, url in _map.items():
        if key in t:
            return url
    # 2) fuzzy match (closest key above threshold)
    keys = list(_map.keys())
    best = difflib.get_close_matches(t, keys, n=1, cutoff=0.72)
    if best:
        return _map[best[0]]
    # 3) try token-level fuzzy (for phrases like 'modern clean minimal feel')
    tokens = t.split()
    for window in range(min(4, len(tokens)), 0, -1):
        for i in range(len(tokens) - window + 1):
            phrase = " ".join(tokens[i:i + window])
            best = difflib.get_close_matches(phrase, keys, n=1, cutoff=0.85)
            if best:
                return _map[best[0]]
    return ""
