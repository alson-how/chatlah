"""Content retrieval and search functionality for RAG system."""

from typing import List, Dict, Any
from app.indexer import collection, embed_texts

def search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search for relevant content using OpenAI embeddings."""
    try:
        # Generate embedding for the query using OpenAI
        query_embedding = embed_texts([query])[0]
        
        # Search in Chroma using the embedding
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Process results
        hits = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                distance = results['distances'][0][i]
                # For cosine distance, similarity = 1 - distance
                similarity = max(0, 1 - distance)
                
                hits.append({
                    'text': results['documents'][0][i],
                    'meta': results['metadatas'][0][i],
                    'similarity_score': similarity
                })
        
        return hits
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []