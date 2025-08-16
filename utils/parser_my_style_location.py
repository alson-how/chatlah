# parser_my_style_location.py
# Unified parser for STYLE + LOCATION (Malaysia) with fuzzy support

from __future__ import annotations
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

# Optional fuzzy support (recommended). If not installed, code still runs without it.
try:
    from rapidfuzz import process, fuzz
    HAS_FUZZ = True
except Exception:
    HAS_FUZZ = False

# -----------------------
# Normalization utilities
# -----------------------

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.lower()
    s = re.sub(r"[^\w\s\-'/]", " ", s)  # keep letters/digits/space/-/'/
    s = re.sub(r"\s+", " ", s).strip()
    return s

# -----------------------
# STYLE lexicon + mapping
# -----------------------

STYLE_KEYWORDS: Dict[str, List[str]] = {
    # Map canonical theme -> common keywords/phrases (expand freely)
    "modern minimalist": [
        "modern minimalist", "minimalist", "minimal", "clean modern", "sleek",
        "simple clean", "streamlined", "clutter free"
    ],
    "natural warmth": [
        "natural warmth", "warm neutral", "neutral palette", "earthy",
        "connection to nature", "cozy warm", "layered lighting", "comfort first"
    ],
    "serene elegance": [
        "serene elegance", "soothing", "calm", "gallery like", "warm monochrome",
        "rounded millwork", "handle less cabinetry"
    ],
    "natural harmony": [
        "natural harmony", "minimalist functionality", "modern elegance",
        "neutral palette", "curated comfort"
    ],
    "playful vibrant retail": [
        "playful", "vibrant", "instagrammable", "retail space", "commercial",
        "led lighting", "fun vibe"
    ],
    "modern industrial accents": [
        "industrial", "industrial accents", "modern industrial",
        "cement screed", "exposed brick", "industrial vibe"
    ],
    # Generic triggers (kept last; we down-rank them)
    "generic": [
        "modern", "contemporary", "classic", "traditional", "luxury",
        "elegant", "rustic", "scandinavian", "mid century", "mid-century",
        "boho", "bohemian", "farmhouse", "coastal", "nautical",
        "wabi sabi", "zen", "hygge", "art deco", "retro", "vintage",
        "glam", "opulent", "grand", "bold", "pastel", "monochrome",
        "style", "design", "vibe", "theme", "look", "feel", "aesthetic", "decor", "interior"
    ],
}

# Optional: link routing for each canonical theme
THEME_LINKS = {
    "modern minimalist": "https://jablancinteriors.com/portfolio/park-regent-desa-park-city/",
    "natural warmth": "https://jablancinteriors.com/portfolio/88-bandar-utama/",
    "serene elegance": "https://jablancinteriors.com/portfolio/3213-the-arcuz/",
    "natural harmony": "https://jablancinteriors.com/portfolio/third-avenus-cyberjaya/",
    "playful vibrant retail": "https://jablancinteriors.com/portfolio/eureka-midvalley/",
    "modern industrial accents": "https://jablancinteriors.com/portfolio/eureka-setia-city-mall/",
}

# Flatten a searchable list for fuzzy
STYLE_TERMS: List[Tuple[str, str]] = []  # (term, theme)
for theme, terms in STYLE_KEYWORDS.items():
    for t in terms:
        STYLE_TERMS.append((norm(t), theme))

# -----------------------
# LOCATION aliases (MY)
# -----------------------

CITY_ALIASES = {
    # Abbreviations first
    "kl": "Kuala Lumpur",
    "pj": "Petaling Jaya",
    "jb": "Johor Bahru",
    "kk": "Kota Kinabalu",
    # Klang Valley / popular areas
    "kuala lumpur": "Kuala Lumpur",
    "petaling jaya": "Petaling Jaya",
    "subang jaya": "Subang Jaya",
    "shah alam": "Shah Alam",
    "ampang": "Ampang",
    "cheras": "Cheras",
    "gombak": "Gombak",
    "kepong": "Kepong",
    "puchong": "Puchong",
    "kajang": "Kajang",
    "bangsar": "Bangsar",
    "damansara": "Damansara",
    "mont kiara": "Mont Kiara",
    "desa parkcity": "Desa ParkCity",
    "setia alam": "Setia Alam",
    "sunway": "Sunway",
    "usj": "USJ",
    "klang": "Klang",
    # States & major cities nationwide
    "penang": "Penang",
    "george town": "George Town",
    "ipoh": "Ipoh",
    "perak": "Perak",
    "seremban": "Seremban",
    "negeri sembilan": "Negeri Sembilan",
    "kuantan": "Kuantan",
    "pahang": "Pahang",
    "kota bharu": "Kota Bharu",
    "kelantan": "Kelantan",
    "alor setar": "Alor Setar",
    "kedah": "Kedah",
    "kangar": "Kangar",
    "perlis": "Perlis",
    "kuching": "Kuching",
    "sarawak": "Sarawak",
    "miri": "Miri",
    "sibu": "Sibu",
    "kota kinabalu": "Kota Kinabalu",
    "sabah": "Sabah",
    "sandakan": "Sandakan",
    "tawau": "Tawau",
    "putrajaya": "Putrajaya",
    "cyberjaya": "Cyberjaya",
    "melaka": "Melaka",
    "malacca": "Melaka",
    "johor bahru": "Johor Bahru",
    "johor": "Johor",
    "sepang": "Sepang",
    "nilai": "Nilai",
    "bangi": "Bangi",
    "port dickson": "Port Dickson",
}

# Condo/building suffixes to detect building names
RESIDENCE_SUFFIXES = [
    "residence", "residences", "residential", "condo", "condominium",
    "apartment", "apartments", "suite", "suites",
    "soho", "sofo", "serviced residence"
]

LOCATION_HINTS_RE = re.compile(r"\b(in|at|near|around|area|located in|based in|around the)\b", re.I)

# Also a flat set of location terms for fuzzy
LOCATION_TERMS = list(CITY_ALIASES.keys())

# -----------------------
# STYLE detection
# -----------------------

def extract_style(text: str, fuzzy: bool = True) -> Optional[Dict[str, str]]:
    t = norm(text)

    # Exact/substring pass, prefer most specific (longest)
    best = None  # (theme, term, length)
    for term, theme in STYLE_TERMS:
        if term and (term in t or re.search(rf"\b{re.escape(term)}\b", t)):
            if (best is None) or (len(term) > best[2]):
                best = (theme, term, len(term))

    # Fuzzy fallback for typos (e.g., "minamalist")
    if best is None and fuzzy and HAS_FUZZ:
        candidates = [term for term, _ in STYLE_TERMS]
        match = process.extractOne(t, candidates, scorer=fuzz.partial_ratio)
        if match and match[1] >= 90:  # threshold; tune 85–92
            term = match[0]
            # find theme
            for kterm, ktheme in STYLE_TERMS:
                if kterm == term:
                    best = (ktheme, kterm, len(kterm))
                    break

    if best:
        theme, term, _ = best
        # Down-rank "generic" unless nothing else
        if theme == "generic":
            # Do we also have a specific non-generic match? already handled above; here generic only
            pass
        return {
            "theme": theme,
            "matched": term,
            "link": THEME_LINKS.get(theme, "")
        }
    return None

# -----------------------
# LOCATION detection
# -----------------------

def _try_alias_lookup(candidate: str) -> Optional[str]:
    cand = norm(candidate)
    # longest-first exact alias
    for alias in sorted(CITY_ALIASES.keys(), key=lambda x: -len(x)):
        if cand == alias:
            return CITY_ALIASES[alias]
    # fuzzy alias
    if HAS_FUZZ:
        match = process.extractOne(cand, LOCATION_TERMS, scorer=fuzz.ratio)
        if match and match[1] >= 90:
            return CITY_ALIASES.get(match[0], None)
    return None

def _extract_building_like(text_norm: str) -> Optional[str]:
    # Search patterns like "Park Regent Residence", "The Arcuz Condominium"
    for suf in RESIDENCE_SUFFIXES:
        pat = re.compile(rf"\b([a-z][a-z '\-]{{2,40}})\s+{re.escape(suf)}\b", re.I)
        m = pat.search(text_norm)
        if m:
            name = (m.group(0)).strip()
            # Title case nicely
            return " ".join(w.capitalize() for w in name.split())
    return None

def extract_location(text: str) -> Optional[str]:
    t = " " + norm(text) + " "

    # 1) Direct alias scan (contains)
    for alias in sorted(CITY_ALIASES.keys(), key=lambda x: -len(x)):
        if f" {alias} " in t:
            return CITY_ALIASES[alias]

    # 2) "in/at/near …" pattern
    m = LOCATION_HINTS_RE.search(t)
    if m:
        span_end = m.end()
        cand = t[span_end:].strip()
        cand = re.split(r"[.,;!?]", cand)[0]  # up to punctuation
        cand = cand[:50]  # limit
        # n-gram scan up to 3 tokens
        toks = [w for w in cand.split() if w]
        for n in (3, 2, 1):
            for i in range(0, max(0, len(toks)-n+1)):
                ng = " ".join(toks[i:i+n])
                mapped = _try_alias_lookup(ng)
                if mapped:
                    return mapped
        # building-like
        b = _extract_building_like(cand)
        if b:
            return b

    # 3) building-like anywhere
    b2 = _extract_building_like(t)
    if b2:
        return b2

    # 4) fuzzy alias anywhere
    if HAS_FUZZ:
        # try the whole text against alias list (coarse)
        match = process.extractOne(t, LOCATION_TERMS, scorer=fuzz.partial_ratio)
        if match and match[1] >= 90:
            return CITY_ALIASES.get(match[0], None)

    return None

# -----------------------
# MASTER entrypoint
# -----------------------

def parse_message(text: str) -> Dict[str, Optional[str]]:
    style = extract_style(text)
    location = extract_location(text)
    return {
        "style_theme": style["theme"] if style else None,
        "style_matched": style["matched"] if style else None,
        "style_link": style["link"] if style else None,
        "location": location
    }