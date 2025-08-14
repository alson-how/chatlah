"""Pydantic models for API request and response validation."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class CrawlRequest(BaseModel):
    """Request model for crawling a website."""
    target_url: HttpUrl = Field(..., description="URL to crawl")
    max_pages: int = Field(default=10, ge=1, le=100, description="Maximum number of pages to crawl")
    include_subdomains: bool = Field(default=False, description="Whether to include subdomains")


class CrawlResponse(BaseModel):
    """Response model for crawl operation."""
    success: bool
    pages_crawled: int
    chunks_indexed: int
    message: str


class CrawledPage(BaseModel):
    """Model representing a crawled page."""
    url: str = Field(..., description="Page URL")
    title: str = Field(default="", description="Page title")  
    chunks_count: int = Field(..., description="Number of content chunks from this page")
    last_crawled: Optional[str] = Field(None, description="When the page was last crawled")


class AskRequest(BaseModel):
    """Request model for asking questions."""
    question: str = Field(..., min_length=1, max_length=1000, description="Question to ask")
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Maximum number of results to return")
    tone_type: Optional[str] = Field(default="customer_support", description="Response tone type (customer_support, technical, casual)")


class SourceDocument(BaseModel):
    """Model representing a source document with citation."""
    content: str = Field(..., description="Relevant content excerpt")
    url: str = Field(..., description="Source URL")
    title: str = Field(default="", description="Page title")
    similarity_score: float = Field(..., description="Similarity score")


class AskResponse(BaseModel):
    """Response model for question answering."""
    answer: str = Field(..., description="Generated answer")
    sources: List[str] = Field(..., description="Source URLs used for the answer")


class ChatRequest(BaseModel):
    """Request model for chat conversation."""
    thread_id: str = Field(..., description="Conversation thread ID")
    user_message: str = Field(..., min_length=1, max_length=1000, description="User message")
    name: str = Field(default="Mei Yee", description="Business owner name")
    company: str = Field(default="Jablanc Interior", description="Company name")
    portfolio_url: str = Field(default="", description="Portfolio URL (optional)")


class ChatResponse(BaseModel):
    """Response model for chat conversation."""
    answer: str = Field(..., description="Assistant response")
    sources: Optional[List[str]] = Field(default=[], description="Source URLs used for the answer")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    version: str
    database_status: str
    indexed_documents: int


class IndexStats(BaseModel):
    """Statistics about the indexed content."""
    total_documents: int
    total_chunks: int
    collection_name: str
    last_updated: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: str
    status_code: int
