# utils/location.py
import re

def extract_location(text: str) -> str:
    """Extract location information from user message."""
    text = text.lower().strip()
    
    # Malaysian location patterns
    patterns = [
        r"(?:in|at|from|located at) ([a-zA-Z\s,]+(?:kl|kuala lumpur|pj|petaling jaya|shah alam|subang|klang|ampang|cheras|mont kiara|bangsar|damansara|ttdi|sri hartamas|bukit jalil|mid valley|kepong|wangsa maju|setapak|kajang|cyberjaya|putrajaya|seremban|johor bahru|penang|ipoh|kota kinabalu|kuching))",
        r"my (?:house|home|office|shop|place) (?:is )?(?:in|at) ([a-zA-Z\s,]+)",
        r"(?:condo|apartment|house|office|shop) in ([a-zA-Z\s,]+)",
        r"(?:at|in) ([a-zA-Z\s,]+(?:heights|residences|suites|tower|gardens|park|mall|plaza))",
        r"location is ([a-zA-Z\s,]+)",
        r"address is ([a-zA-Z\s,]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip().title()
            # Clean up common words
            location = re.sub(r'\b(Is|The|At|In|My|House|Home|Office|Shop|Place|Condo|Apartment)\b', '', location).strip()
            if location and len(location) > 2:
                return location
    
    return ""

def mentions_location_need(text: str) -> bool:
    """Check if the message indicates they need location info."""
    text = text.lower()
    location_keywords = [
        "house", "home", "condo", "apartment", "office", "shop", "place", 
        "location", "address", "where", "renovation", "interior design"
    ]
    return any(keyword in text for keyword in location_keywords)