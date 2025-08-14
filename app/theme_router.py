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
    t = norm(text)
    # direct/substring
    for k, u in MAP.items():
        if k in t: return u
    # fuzzy whole-string
    keys = list(MAP.keys())
    hit = difflib.get_close_matches(t, keys, n=1, cutoff=0.75)
    if hit: return MAP[hit[0]]
    # token windows
    toks = t.split()
    for w in range(min(4, len(toks)), 0, -1):
        for i in range(len(toks) - w + 1):
            p = " ".join(toks[i:i + w])
            hit = difflib.get_close_matches(p, keys, n=1, cutoff=0.85)
            if hit: return MAP[hit[0]]
    return ""
