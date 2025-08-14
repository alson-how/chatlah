"""Content retrieval and response generation for RAG system."""

from typing import List, Dict, Any, Optional
from app.indexer import ContentIndexer
from app.models import SourceDocument, AskResponse
from app.config import settings


class ContentRetriever:
    """Handles content retrieval and answer generation."""
    
    def __init__(self):
        self.indexer = ContentIndexer()
    
    def retrieve_relevant_content(self, question: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant content for a given question."""
        try:
            # Search for similar content
            similar_content = self.indexer.search_similar_content(
                query=question,
                n_results=max_results
            )
            
            # Filter by similarity threshold
            filtered_content = [
                content for content in similar_content
                if content['similarity_score'] >= settings.similarity_threshold
            ]
            
            return filtered_content
        
        except Exception as e:
            raise Exception(f"Failed to retrieve relevant content: {str(e)}")
    
    def format_source_documents(self, content_list: List[Dict[str, Any]]) -> List[SourceDocument]:
        """Format retrieved content into SourceDocument objects."""
        source_docs = []
        
        for content in content_list:
            metadata = content.get('metadata', {})
            
            source_doc = SourceDocument(
                content=content['content'],
                url=metadata.get('url', ''),
                title=metadata.get('title', 'Untitled'),
                similarity_score=content['similarity_score']
            )
            
            source_docs.append(source_doc)
        
        return source_docs
    
    def generate_grounded_answer(self, question: str, source_documents: List[SourceDocument]) -> str:
        """Generate a grounded answer based on retrieved source documents."""
        if not source_documents:
            return "I don't have enough relevant information to answer your question. Please make sure the website content has been indexed."
        
        # Create context from source documents
        context_parts = []
        for i, doc in enumerate(source_documents, 1):
            context_parts.append(f"Source {i} ({doc.url}):\n{doc.content}")
        
        context = "\n\n".join(context_parts)
        
        # Generate answer based on context
        # This is a simple implementation - in production you might use an LLM
        answer_parts = []
        
        # Add introduction
        answer_parts.append(f"Based on the indexed content, here's what I found regarding your question: '{question}'")
        
        # Add relevant information with citations
        for i, doc in enumerate(source_documents, 1):
            if len(doc.content) > 200:
                snippet = doc.content[:200] + "..."
            else:
                snippet = doc.content
            
            answer_parts.append(f"\nFrom {doc.title} ({doc.url}):")
            answer_parts.append(f"{snippet}")
            answer_parts.append(f"(Relevance score: {doc.similarity_score:.2f})")
        
        # Add conclusion
        if len(source_documents) > 1:
            answer_parts.append(f"\nThis answer is based on {len(source_documents)} relevant sources from the indexed website content.")
        else:
            answer_parts.append(f"\nThis answer is based on 1 relevant source from the indexed website content.")
        
        return "\n".join(answer_parts)
    
    def calculate_confidence(self, source_documents: List[SourceDocument]) -> float:
        """Calculate confidence score based on source documents."""
        if not source_documents:
            return 0.0
        
        # Calculate average similarity score
        avg_similarity = sum(doc.similarity_score for doc in source_documents) / len(source_documents)
        
        # Boost confidence if we have multiple high-quality sources
        confidence = avg_similarity
        
        if len(source_documents) >= 3:
            confidence = min(confidence * 1.1, 1.0)
        
        if avg_similarity >= 0.9:
            confidence = min(confidence * 1.05, 1.0)
        
        return round(confidence, 3)
    
    def ask_question(self, question: str, max_results: int = 5) -> AskResponse:
        """Process a question and return a grounded answer with sources."""
        try:
            # Retrieve relevant content
            relevant_content = self.retrieve_relevant_content(question, max_results)
            
            # Format source documents
            source_documents = self.format_source_documents(relevant_content)
            
            # Generate grounded answer
            answer = self.generate_grounded_answer(question, source_documents)
            
            # Calculate confidence
            confidence = self.calculate_confidence(source_documents)
            
            return AskResponse(
                answer=answer,
                sources=source_documents,
                confidence=confidence,
                question=question
            )
        
        except Exception as e:
            # Return error response with empty sources
            return AskResponse(
                answer=f"I encountered an error while processing your question: {str(e)}",
                sources=[],
                confidence=0.0,
                question=question
            )
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get current database status."""
        try:
            stats = self.indexer.get_collection_stats()
            return {
                "status": "healthy" if stats["total_documents"] > 0 else "empty",
                "total_documents": stats["total_documents"],
                "collection_name": stats["collection_name"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "total_documents": 0,
                "collection_name": settings.chroma_collection_name
            }
