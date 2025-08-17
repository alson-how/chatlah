# app/portfolio_preview.py
from __future__ import annotations
from typing import Optional, List, Dict
from app.retriever import search

def portfolio_preview(max_items: int = 3) -> Optional[str]:
    """Generate portfolio preview using the existing search functionality."""
    try:
        # Use existing search function with portfolio-focused query
        results = search("portfolio projects interior design examples", top_k=max_items)
        
        if not results:
            return None
            
        items = []
        for result in results:
            # Extract metadata from search results
            metadata = result.get('meta', {})
            title = metadata.get('title', '').strip()
            url = metadata.get('url', '')
            
            if title and url:
                items.append(f"{title} ({url})")
            elif url:
                # Fallback to just URL if no title
                items.append(url)
                
            if len(items) >= max_items:
                break
                
        if not items:
            return None
            
        return "Examples: " + "; ".join(items)
        
    except Exception as e:
        print(f"Error generating portfolio preview: {e}")
        return None
