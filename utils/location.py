# utils/location.py
import re

def extract_location(text: str) -> str:
    """Extract location information from user message."""
    text = text.lower().strip()
    
    # Malaysian location patterns - more flexible approach
    patterns = [
        r"(?:in|at|from|located at)\s+([a-zA-Z\s,]+)",
        r"my (?:house|home|office|shop|place) (?:is )?(?:in|at)\s+([a-zA-Z\s,]+)",
        r"(?:condo|apartment|house|office|shop) in\s+([a-zA-Z\s,]+)",
        r"(?:at|in)\s+([a-zA-Z\s,]+(?:heights|residences|suites|tower|gardens|park|mall|plaza|alam))",
        r"location is\s+([a-zA-Z\s,]+)",
        r"address is\s+([a-zA-Z\s,]+)",
        # Remove this overly broad pattern that captures names
    ]
    
    # Common Malaysian location keywords to help validate
    malaysian_indicators = [
        "kl", "kuala lumpur", "pj", "petaling jaya", "shah alam", "subang", "klang", 
        "ampang", "cheras", "mont kiara", "bangsar", "damansara", "ttdi", "sri hartamas", 
        "bukit jalil", "mid valley", "kepong", "wangsa maju", "setapak", "kajang", 
        "cyberjaya", "putrajaya", "seremban", "johor bahru", "penang", "ipoh", 
        "kota kinabalu", "kuching", "setia alam", "ara damansara", "sunway", "usj",
        "ss2", "ss15", "taipan", "kota damansara", "mutiara damansara", "tropicana",
        "gardens", "heights", "residences", "suites", "tower", "park", "mall", "plaza",
        "alam", "jaya", "sri", "taman", "bukit", "bandar"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean up common words and fillers
            location = re.sub(r'\b(Is|The|At|In|My|House|Home|Office|Shop|Place|Condo|Apartment|Hmm|Well|Erm|Um|Oh|Lah|Ah)\b', '', location, flags=re.IGNORECASE).strip()
            location = re.sub(r'[.]{2,}', '', location).strip()  # Remove multiple dots
            
            if location and len(location) > 2:
                # Check if it contains Malaysian location indicators or just accept reasonable length locations
                location_lower = location.lower()
                
                # Filter out style-related words that are not locations
                style_keywords = [
                    # Core design movements
                    "modern", "contemporary", "minimalist", "maximalist",
                    "classic", "traditional", "transitional", "colonial",
                    "industrial", "scandinavian", "mid century", "mid-century",
                    "art deco", "art nouveau", "bauhaus", "brutalist",

                    # Warm/natural/luxury aesthetics
                    "natural", "organic", "warm", "neutral", "earthy",
                    "bohemian", "boho", "eclectic", "rustic", "farmhouse",
                    "country", "tropical", "resort style", "balinese",
                    "mediterranean", "greek", "italian", "japanese zen", "zen",
                    "wabi sabi", "hygge", "coastal", "nautical",

                    # Sleek/elegant aesthetics
                    "elegant", "luxury", "opulent", "grand", "sophisticated",
                    "glam", "glamorous", "hollywood regency",
                    "contemporary luxury", "modern luxury", "serene elegance",

                    # Raw/urban/edgy
                    "raw", "unfinished", "grunge", "urban", "warehouse",
                    "loft style", "modern industrial", "exposed brick",
                    "cement screed", "concrete finish",

                    # Retro/vintage/nostalgic
                    "retro", "vintage", "shabby chic", "victorian",
                    "edwardian", "rococo", "baroque", "antique",

                    # Functional / thematic
                    "functional", "compact", "space saving", "open concept",
                    "gallery like", "instagrammable", "playful", "vibrant",
                    "monochrome", "pastel", "colourful", "bold",
                    "statement", "accent", "feature wall",

                    # Generic words clients often use
                    "style", "design", "vibe", "theme", "look",
                    "feel", "aesthetic", "decor", "interior", "ambience",
                    "atmosphere", "mood", "concept", "inspiration", "trend"
                ]
                
                # Don't extract if it's clearly a style description
                if any(style_word in location_lower for style_word in style_keywords):
                    return ""
                
                # Don't extract if it contains person names or typical name patterns
                name_patterns = ["here", "speaking", "this is", "my name", "i am", "i'm", "call me"]
                if any(pattern in location_lower for pattern in name_patterns):
                    return ""
                
                # Only accept if it contains Malaysian location indicators - be more strict
                if any(indicator in location_lower for indicator in malaysian_indicators):
                    return location.title()
    
    return ""

def mentions_location_need(text: str) -> bool:
    """Check if the message indicates they need location info."""
    text = text.lower()
    location_keywords = [
        "house", "home", "condo", "apartment", "office", "shop", "place", 
        "location", "address", "where", "renovation", "interior design"
    ]
    return any(keyword in text for keyword in location_keywords)