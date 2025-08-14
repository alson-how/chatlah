"""Content indexing and embedding functionality using Chroma."""

import os
import uuid
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.chunking import TextChunker


class ContentIndexer:
    """Handles content indexing and embedding with Chroma."""
    
    def __init__(self):
        self.chunk_processor = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        # Initialize Chroma client
        self._init_chroma_client()
    
    def _init_chroma_client(self):
        """Initialize Chroma database client."""
        # Ensure data directory exists
        os.makedirs(settings.chroma_db_path, exist_ok=True)
        
        # Initialize persistent Chroma client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_db_path
        )
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(
                name=settings.chroma_collection_name
            )
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "Website content for RAG system"}
            )
    
    def index_page_content(self, page_data: Dict[str, Any]) -> Dict[str, int]:
        """Index content from a single page."""
        try:
            # Process page content into chunks
            chunks = self.chunk_processor.process_page_content(page_data)
            
            if not chunks:
                return {"chunks_processed": 0, "chunks_indexed": 0}
            
            # Prepare data for indexing
            chunk_texts = [chunk['content'] for chunk in chunks]
            chunk_ids = [str(uuid.uuid4()) for _ in chunks]
            
            # Prepare metadata
            metadatas = []
            for chunk in chunks:
                metadata = chunk['metadata'].copy()
                # Ensure all metadata values are strings
                for key, value in metadata.items():
                    if value is not None:
                        metadata[key] = str(value)
                metadatas.append(metadata)
            
            # Add to Chroma collection
            self.collection.add(
                documents=chunk_texts,
                metadatas=metadatas,
                ids=chunk_ids
            )
            
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
                "collection_name": settings.chroma_collection_name,
                "embedding_model": "chromadb-default-ef"
            }
        except Exception as e:
            raise Exception(f"Failed to get collection stats: {str(e)}")
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection."""
        try:
            # Delete the collection and recreate it
            self.chroma_client.delete_collection(name=settings.chroma_collection_name)
            self.collection = self.chroma_client.create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "Website content for RAG system"}
            )
            return True
        except Exception as e:
            print(f"Failed to clear collection: {str(e)}")
            return False
    
    def search_similar_content(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar content in the collection."""
        try:
            # Search in Chroma
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            similar_content = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    similar_content.append({
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': max(0, 1 - results['distances'][0][i])  # Convert distance to similarity
                    })
            
            return similar_content
            
        except Exception as e:
            raise Exception(f"Failed to search similar content: {str(e)}")
