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
        r"^(?:hmm\.{2,3}|well\.{2,3}|erm\.{2,3}|um\.{2,3})?([a-zA-Z\s,]+?)(?:\s+oh|lah|ah)?$"  # Malaysian casual responses
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
                if (any(indicator in location_lower for indicator in malaysian_indicators) or 
                    len(location.split()) <= 3):  # Accept short location names
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