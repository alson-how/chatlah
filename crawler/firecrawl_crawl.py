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
            
            # Extract content directly from scraped_data attributes
            page_data = {
                'url': url,
                'title': getattr(scraped_data, 'title', '') or '',
                'description': getattr(scraped_data, 'description', '') or '',
                'content': getattr(scraped_data, 'markdown', '') or '',
                'html': getattr(scraped_data, 'html', '') if include_html else '',
                'metadata': {
                    'source': 'firecrawl',
                    'scraped_at': time.time(),
                    'status_code': getattr(scraped_data, 'statusCode', None),
                    'content_type': 'text/html'
                }
            }
            
            # Try to get metadata if available
            if hasattr(scraped_data, 'metadata'):
                metadata_obj = scraped_data.metadata
                if hasattr(metadata_obj, 'title'):
                    page_data['title'] = metadata_obj.title or ''
                if hasattr(metadata_obj, 'description'):
                    page_data['description'] = metadata_obj.description or ''
            
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
            pages = []
            
            # Try multi-page crawling first
            if max_pages > 1:
                try:
                    # Use Firecrawl's crawl functionality for multiple pages
                    # Using correct API parameters from 2024 documentation
                    from firecrawl import ScrapeOptions
                    
                    scrape_options = ScrapeOptions(
                        formats=['markdown'],
                        only_main_content=True,
                        exclude_tags=['nav', 'footer', '.sidebar', '#sidebar'],
                        timeout=15000
                    )
                    
                    crawl_result = self.app.crawl_url(
                        url=url,
                        limit=max_pages,
                        scrape_options=scrape_options,
                        max_depth=2,
                        allow_backward_links=False
                    )
                    
                    if hasattr(crawl_result, 'success') and crawl_result.success:
                        # Process crawled pages
                        crawled_pages = getattr(crawl_result, 'data', [])
                        for i, page_data in enumerate(crawled_pages):
                            # Extract URL from the metadata which contains the actual page URLs
                            page_url = None
                            
                            # First try to get URL from metadata (this is where the real URLs are)
                            if hasattr(page_data, 'metadata') and page_data.metadata:
                                page_url = getattr(page_data.metadata, 'url', None) or getattr(page_data.metadata, 'sourceURL', None)
                            
                            # Fallback to direct attributes
                            if not page_url:
                                page_url = getattr(page_data, 'url', None) or getattr(page_data, 'sourceURL', None)
                            
                            # Clean up the URL (remove utm parameters for cleaner display)
                            if page_url and '?' in page_url:
                                page_url = page_url.split('?')[0]
                            
                            # Use base URL as absolute fallback
                            if not page_url:
                                page_url = url
                            
                            page = {
                                'url': page_url,
                                'title': getattr(page_data, 'title', '') or '',
                                'description': getattr(page_data, 'description', '') or '',
                                'content': getattr(page_data, 'markdown', '') or '',
                                'html': getattr(page_data, 'html', '') if False else '',
                                'metadata': {
                                    'source': 'firecrawl_crawl',
                                    'scraped_at': time.time(),
                                    'status_code': getattr(page_data, 'statusCode', None),
                                    'content_type': 'text/html'
                                }
                            }
                            pages.append(page)
                    
                    if pages:
                        print(f"Successfully crawled {len(pages)} pages using multi-page crawling")
                        return pages
                    
                except Exception as e:
                    print(f"Multi-page crawling failed: {str(e)}. Falling back to single page crawling.")
            
            # Fallback to single page crawling
            main_page = self.crawl_single_page(url)
            if main_page:
                pages.append(main_page)
                print(f"Successfully crawled 1 page using single-page crawling")
            
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
