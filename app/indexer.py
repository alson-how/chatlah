"""Content indexing and embedding functionality using Chroma."""

import os
import uuid
from typing import List, Dict, Any, Optional
# import chromadb
# from chromadb.config import Settings as ChromaSettings
# from sentence_transformers import SentenceTransformer
from app.config import settings
from app.chunking import TextChunker


class ContentIndexer:
    """Handles content indexing and embedding with simple storage."""
    
    def __init__(self):
        self.chunk_processor = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        # Simple in-memory storage for now (will be replaced with real vector DB)
        self.indexed_content = []
        self.document_count = 0
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate simple embeddings for a list of texts (simplified for demo)."""
        # Simple word frequency-based embeddings for demo purposes
        # In production, this would use a proper embedding model
        embeddings = []
        for text in texts:
            words = text.lower().split()
            # Simple frequency vector (first 100 most common words)
            embedding = [float(words.count(str(i))) for i in range(100)]
            embeddings.append(embedding)
        return embeddings
    
    def index_page_content(self, page_data: Dict[str, Any]) -> Dict[str, int]:
        """Index content from a single page."""
        try:
            # Process page content into chunks
            chunks = self.chunk_processor.process_page_content(page_data)
            
            if not chunks:
                return {"chunks_processed": 0, "chunks_indexed": 0}
            
            # Store in simple memory structure for demo
            for chunk in chunks:
                indexed_item = {
                    "id": str(uuid.uuid4()),
                    "content": chunk['content'],
                    "metadata": chunk['metadata']
                }
                self.indexed_content.append(indexed_item)
            
            self.document_count += 1
            
            return {
                "chunks_processed": len(chunks),
                "chunks_indexed": len(chunks)
            }
            
        except Exception as e:
            raise Exception(f"Failed to index page content: {str(e)}")
    
    def index_multiple_pages(self, pages_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Index content from multiple pages."""
        total_processed = 0
        total_indexed = 0
        failed_pages = 0
        
        for page_data in pages_data:
            try:
                result = self.index_page_content(page_data)
                total_processed += result["chunks_processed"]
                total_indexed += result["chunks_indexed"]
            except Exception as e:
                failed_pages += 1
                print(f"Failed to index page {page_data.get('url', 'unknown')}: {str(e)}")
        
        return {
            "pages_total": len(pages_data),
            "pages_successful": len(pages_data) - failed_pages,
            "pages_failed": failed_pages,
            "chunks_processed": total_processed,
            "chunks_indexed": total_indexed
        }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed collection."""
        return {
            "total_documents": len(self.indexed_content),
            "collection_name": settings.chroma_collection_name,
            "embedding_model": settings.embedding_model
        }
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection."""
        try:
            self.indexed_content = []
            self.document_count = 0
            return True
        except Exception as e:
            print(f"Failed to clear collection: {str(e)}")
            return False
    
    def search_similar_content(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar content in the collection."""
        try:
            # Simple keyword search for demo (will be replaced with vector search)
            query_words = query.lower().split()
            similar_content = []
            
            for item in self.indexed_content:
                content_words = item['content'].lower().split()
                # Simple relevance score based on word overlap
                common_words = set(query_words) & set(content_words)
                if common_words:
                    similarity_score = len(common_words) / max(len(query_words), len(content_words))
                    if similarity_score >= 0.1:  # Basic threshold
                        similar_content.append({
                            'content': item['content'],
                            'metadata': item['metadata'],
                            'similarity_score': similarity_score
                        })
            
            # Sort by similarity score and return top results
            similar_content.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_content[:n_results]
            
        except Exception as e:
            raise Exception(f"Failed to search similar content: {str(e)}")
