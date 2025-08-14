"""Content indexing and embedding functionality using OpenAI and Chroma."""

import os
import hashlib
import requests
import time
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import OPENAI_API_KEY, CHROMA_DIR, COLLECTION_NAME
from app.chunking import TextChunker

# Chroma persistent client
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI's text-embedding-3-large model."""
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "text-embedding-3-large", "input": texts},
        timeout=120
    )
    r.raise_for_status()
    data = r.json()
    return [d["embedding"] for d in data["data"]]

def upsert_chunks(chunks: List[Dict]):
    """Upsert chunks into ChromaDB with OpenAI embeddings."""
    if not chunks:
        return
    
    # Clean and validate data
    valid_chunks = []
    for c in chunks:
        # Ensure all required fields are present and valid
        text = str(c.get("text", "")).strip()
        url = str(c.get("url", "unknown")).strip()
        title = str(c.get("title", "Untitled")).strip()
        chunk_idx = c.get("chunk_idx", 0)
        scraped_at = str(c.get("scraped_at", ""))
        
        if not text:  # Skip empty chunks
            continue
            
        valid_chunks.append({
            "text": text,
            "url": url,
            "title": title,
            "chunk_idx": int(chunk_idx) if isinstance(chunk_idx, (int, float)) else 0,
            "scraped_at": scraped_at
        })
    
    if not valid_chunks:
        return
    
    texts = [c["text"] for c in valid_chunks]
    ids = [hashlib.sha256(f'{c["url"]}-{c["chunk_idx"]}-{c["text"]}'.encode()).hexdigest() for c in valid_chunks]
    
    # Create clean metadata - ensure all values are strings, ints, floats, or bools
    metas = []
    for c in valid_chunks:
        meta = {
            "url": c["url"],
            "title": c["title"],
            "chunk_idx": c["chunk_idx"],
            "scraped_at": c["scraped_at"] if c["scraped_at"] else "unknown"
        }
        metas.append(meta)

    embeddings = embed_texts(texts)
    collection.upsert(ids=ids, embeddings=embeddings, metadatas=metas, documents=texts)


class ContentIndexer:
    """Handles content indexing and embedding with OpenAI and Chroma."""
    
    def __init__(self):
        # Initialize text chunker
        self.chunk_processor = TextChunker(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Initialize Chroma client
        self._init_chroma_client()
    
    def _init_chroma_client(self):
        """Initialize Chroma database client."""
        # Ensure data directory exists
        os.makedirs(CHROMA_DIR, exist_ok=True)
        
        # Use the global client and collection
        self.chroma_client = client
        self.collection = collection
    
    def index_page_content(self, page_data: Dict[str, Any]) -> Dict[str, int]:
        """Index content from a single page using OpenAI embeddings."""
        try:
            # Process page content into chunks
            chunks = self.chunk_processor.process_page_content(page_data)
            
            if not chunks:
                return {"chunks_processed": 0, "chunks_indexed": 0}
            
            # Convert to the format expected by upsert_chunks
            chunk_data = []
            for i, chunk in enumerate(chunks):
                chunk_data.append({
                    "text": chunk['content'],
                    "url": chunk['metadata'].get('url', ''),
                    "title": chunk['metadata'].get('title', 'Untitled'),
                    "chunk_idx": i,
                    "scraped_at": str(time.time())
                })
            
            # Use the new OpenAI-based upsert function
            upsert_chunks(chunk_data)
            
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
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": COLLECTION_NAME,
                "embedding_model": "text-embedding-3-large"
            }
        except Exception as e:
            raise Exception(f"Failed to get collection stats: {str(e)}")
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection."""
        try:
            # Delete the collection and recreate it
            self.chroma_client.delete_collection(name=COLLECTION_NAME)
            self.collection = self.chroma_client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Website content for RAG system"}
            )
            return True
        except Exception as e:
            print(f"Failed to clear collection: {str(e)}")
            return False
    
    def search_similar_content(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar content in the collection using OpenAI embeddings."""
        try:
            # Generate embedding for the query using OpenAI
            query_embedding = embed_texts([query])[0]
            
            # Search in Chroma using the embedding
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            similar_content = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    distance = results['distances'][0][i]
                    # For cosine distance, similarity = 1 - distance
                    similarity = max(0, 1 - distance)
                    
                    similar_content.append({
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': similarity
                    })
            
            return similar_content
            
        except Exception as e:
            raise Exception(f"Failed to search similar content: {str(e)}")
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get database status for health checks."""
        try:
            count = self.collection.count()
            return {
                "status": "healthy",
                "total_documents": count,
                "embedding_model": "text-embedding-3-large"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "total_documents": 0,
                "error": str(e)
            }