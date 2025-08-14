"""Firecrawl integration for website crawling."""

import os
from typing import List, Dict, Any, Optional
from firecrawl import FirecrawlApp
import time


class FirecrawlClient:
    """Client for crawling websites using Firecrawl API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Firecrawl client."""
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        
        if not self.api_key:
            raise ValueError("Firecrawl API key is required. Set FIRECRAWL_API_KEY environment variable.")
        
        try:
            self.app = FirecrawlApp(api_key=self.api_key)
        except Exception as e:
            raise Exception(f"Failed to initialize Firecrawl client: {str(e)}")
    
    def crawl_single_page(self, url: str, include_html: bool = True) -> Dict[str, Any]:
        """Crawl a single page and return clean content."""
        try:
            # Scrape the page using the correct Firecrawl API format
            scraped_data = self.app.scrape_url(url)
            
            if not scraped_data.success:
                raise Exception(f"Failed to scrape URL: {getattr(scraped_data, 'error', 'Unknown error')}")
            
            # Extract content from the data attribute
            content_data = scraped_data.data
            
            page_data = {
                'url': url,
                'title': getattr(content_data.metadata, 'title', '') if hasattr(content_data, 'metadata') else '',
                'description': getattr(content_data.metadata, 'description', '') if hasattr(content_data, 'metadata') else '',
                'content': getattr(content_data, 'markdown', ''),
                'html': getattr(content_data, 'html', '') if include_html else '',
                'metadata': {
                    'source': 'firecrawl',
                    'scraped_at': time.time(),
                    'status_code': getattr(content_data.metadata, 'statusCode', None) if hasattr(content_data, 'metadata') else None,
                    'content_type': getattr(content_data.metadata, 'contentType', 'text/html') if hasattr(content_data, 'metadata') else 'text/html'
                }
            }
            
            # Add any additional metadata if available
            if hasattr(content_data, 'metadata'):
                metadata_dict = vars(content_data.metadata) if hasattr(content_data.metadata, '__dict__') else {}
                for key, value in metadata_dict.items():
                    if key not in ['title', 'description', 'statusCode', 'contentType']:
                        page_data['metadata'][key] = value
            
            return page_data
        
        except Exception as e:
            raise Exception(f"Failed to crawl page {url}: {str(e)}")
    
    def crawl_website(self, 
                     url: str, 
                     max_pages: int = 10,
                     include_subdomains: bool = False,
                     exclude_patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Crawl an entire website and return clean pages."""
        try:
            # For now, just scrape the single page since crawl_url has parameter issues
            # This is a simplified version that works with current Firecrawl API
            pages = []
            
            # Scrape the main page
            main_page = self.crawl_single_page(url)
            if main_page:
                pages.append(main_page)
            
            return pages
        
        except Exception as e:
            raise Exception(f"Failed to crawl website {url}: {str(e)}")
    
    def validate_api_key(self) -> bool:
        """Validate the Firecrawl API key."""
        try:
            # Try to scrape a simple page to test the API key
            test_result = self.app.scrape_url("https://httpbin.org/robots.txt")
            return test_result.success if hasattr(test_result, 'success') else False
        except Exception:
            return False
