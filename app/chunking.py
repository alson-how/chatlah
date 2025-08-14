"""Text processing and chunking utilities."""

import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


class TextChunker:
    """Handles text cleaning and chunking operations."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract text."""
        if not html_content:
            return ""
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text and clean it
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\!\?\,\;\:\-\(\)]', '', text)
        
        # Remove multiple consecutive punctuation
        text = re.sub(r'([.!?]){2,}', r'\1', text)
        
        return text.strip()
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        
        if metadata is None:
            metadata = {}
        
        # Split text into sentences for better chunking
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_metadata = {
                    **metadata,
                    'chunk_index': len(chunks),
                    'chunk_length': current_length
                }
                
                chunks.append({
                    'content': current_chunk.strip(),
                    'metadata': chunk_metadata
                })
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Take last portion of current chunk for overlap
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    # Find the start of the last complete word in overlap
                    overlap_start = overlap_text.rfind(' ')
                    if overlap_start != -1:
                        current_chunk = overlap_text[overlap_start + 1:] + " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    current_chunk = sentence
                
                current_length = len(current_chunk)
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_length = len(current_chunk)
        
        # Add final chunk if it exists
        if current_chunk.strip():
            chunk_metadata = {
                **metadata,
                'chunk_index': len(chunks),
                'chunk_length': len(current_chunk)
            }
            
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': chunk_metadata
            })
        
        return chunks
    
    def process_page_content(self, page_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a page and return chunks with metadata."""
        content = page_data.get('content', '')
        
        # Clean HTML if present, otherwise clean text
        html_content = page_data.get('html', '')
        if html_content:
            cleaned_content = self.clean_html(html_content)
        else:
            cleaned_content = self.clean_text(content)
        
        if not cleaned_content:
            return []
        
        # Prepare metadata - ensure URL is properly extracted  
        url = page_data.get('url', '')
        if not url and 'metadata' in page_data:
            url = page_data['metadata'].get('url', '')
        if not url or url in ['None', 'none', '']:
            # Try alternative URL sources or use a default
            url = page_data.get('sourceURL', 'https://crawled-content')
        
        metadata = {
            'url': url,
            'title': page_data.get('title', '') or 'Untitled',
            'description': page_data.get('description', '') or '',
            'source': 'firecrawl'
        }
        
        # Add any additional metadata from the page
        if 'metadata' in page_data:
            metadata.update(page_data['metadata'])
        
        return self.chunk_text(cleaned_content, metadata)
