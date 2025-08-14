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
            # Scrape the page
            scraped_data = self.app.scrape_url(
                url=url,
                params={
                    'formats': ['markdown', 'html'],
                    'includeTags': ['title', 'meta'],
                    'excludeTags': ['script', 'style', 'nav', 'footer'],
                    'onlyMainContent': True,
                    'waitFor': 1000  # Wait for 1 second for dynamic content
                }
            )
            
            if not scraped_data.get('success', False):
                raise Exception(f"Failed to scrape URL: {scraped_data.get('error', 'Unknown error')}")
            
            # Extract content
            content_data = scraped_data.get('data', {})
            
            page_data = {
                'url': url,
                'title': content_data.get('metadata', {}).get('title', ''),
                'description': content_data.get('metadata', {}).get('description', ''),
                'content': content_data.get('markdown', ''),
                'html': content_data.get('html', '') if include_html else '',
                'metadata': {
                    'source': 'firecrawl',
                    'scraped_at': time.time(),
                    'status_code': content_data.get('metadata', {}).get('statusCode'),
                    'content_type': content_data.get('metadata', {}).get('contentType', 'text/html')
                }
            }
            
            # Add any additional metadata
            metadata = content_data.get('metadata', {})
            for key, value in metadata.items():
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
            if exclude_patterns is None:
                exclude_patterns = [
                    '.*\\.pdf$',
                    '.*\\.jpg$', '.*\\.jpeg$', '.*\\.png$', '.*\\.gif$',
                    '.*\\.zip$', '.*\\.tar$', '.*\\.gz$',
                    '.*/admin/.*', '.*/login.*', '.*/logout.*'
                ]
            
            # Configure crawl parameters
            crawl_params = {
                'crawlerOptions': {
                    'limit': max_pages,
                    'excludes': exclude_patterns,
                    'includes': [],
                    'allowBackwardCrawling': False,
                    'allowExternalContentLinks': include_subdomains
                },
                'pageOptions': {
                    'formats': ['markdown', 'html'],
                    'includeTags': ['title', 'meta'],
                    'excludeTags': ['script', 'style', 'nav', 'footer'],
                    'onlyMainContent': True,
                    'waitFor': 1000
                }
            }
            
            # Start crawl job
            crawl_result = self.app.crawl_url(
                url=url,
                params=crawl_params,
                wait_until_done=True,
                timeout=300  # 5 minutes timeout
            )
            
            if not crawl_result.get('success', False):
                raise Exception(f"Crawl failed: {crawl_result.get('error', 'Unknown error')}")
            
            # Process crawled data
            crawl_data = crawl_result.get('data', [])
            processed_pages = []
            
            for page_data in crawl_data:
                try:
                    processed_page = {
                        'url': page_data.get('metadata', {}).get('sourceURL', ''),
                        'title': page_data.get('metadata', {}).get('title', ''),
                        'description': page_data.get('metadata', {}).get('description', ''),
                        'content': page_data.get('markdown', ''),
                        'html': page_data.get('html', ''),
                        'metadata': {
                            'source': 'firecrawl',
                            'scraped_at': time.time(),
                            'status_code': page_data.get('metadata', {}).get('statusCode'),
                            'content_type': page_data.get('metadata', {}).get('contentType', 'text/html'),
                            'crawl_id': crawl_result.get('jobId', '')
                        }
                    }
                    
                    # Add additional metadata
                    metadata = page_data.get('metadata', {})
                    for key, value in metadata.items():
                        if key not in ['title', 'description', 'sourceURL', 'statusCode', 'contentType']:
                            processed_page['metadata'][key] = value
                    
                    # Only include pages with content
                    if processed_page['content'] or processed_page['html']:
                        processed_pages.append(processed_page)
                
                except Exception as e:
                    print(f"Failed to process page data: {str(e)}")
                    continue
            
            print(f"Successfully crawled {len(processed_pages)} pages from {url}")
            return processed_pages
        
        except Exception as e:
            raise Exception(f"Failed to crawl website {url}: {str(e)}")
    
    def get_crawl_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a crawl job."""
        try:
            status = self.app.check_crawl_status(job_id)
            return status
        except Exception as e:
            raise Exception(f"Failed to get crawl status: {str(e)}")
    
    def validate_api_key(self) -> bool:
        """Validate the Firecrawl API key."""
        try:
            # Try to scrape a simple page to test the API key
            test_result = self.app.scrape_url(
                url="https://httpbin.org/robots.txt",
                params={'formats': ['markdown']}
            )
            return test_result.get('success', False)
        except Exception:
            return False
