"""FastAPI application with health and ask endpoints."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Dict, Any

from app.models import (
    AskRequest, AskResponse, HealthResponse, ErrorResponse,
    CrawlRequest, CrawlResponse
)
from app.retriever import ContentRetriever
from app.config import settings
from app import __version__

# Initialize FastAPI app
app = FastAPI(
    title="RAG System API",
    description="A FastAPI-based RAG system with Firecrawl crawling and Chroma indexing",
    version=__version__
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize retriever
retriever = ContentRetriever()


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            status_code=500
        ).dict()
    )


@app.get("/")
async def root():
    """Serve the main web interface."""
    return FileResponse("static/index.html")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database status
        db_status = retriever.get_database_status()
        
        health_response = HealthResponse(
            status="healthy" if db_status["status"] == "healthy" else "degraded",
            version=__version__,
            database_status=db_status["status"],
            indexed_documents=db_status["total_documents"]
        )
        
        return health_response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question and get a grounded response."""
    try:
        # Validate request
        if not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        # Check if database has content
        db_status = retriever.get_database_status()
        if db_status["total_documents"] == 0:
            return AskResponse(
                answer="No content has been indexed yet. Please run the crawling and indexing pipeline first.",
                sources=[],
                confidence=0.0,
                question=request.question
            )
        
        # Process the question
        response = retriever.ask_question(
            question=request.question,
            max_results=request.max_results
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}"
        )


@app.post("/crawl", response_model=CrawlResponse)
async def crawl_website(request: CrawlRequest):
    """Crawl and index a website."""
    try:
        # Import crawler here to avoid circular imports
        from crawler.firecrawl_crawl import FirecrawlClient
        
        # Validate Firecrawl API key
        if not settings.firecrawl_api_key:
            raise HTTPException(
                status_code=400,
                detail="Firecrawl API key not configured. Please set FIRECRAWL_API_KEY environment variable."
            )
        
        # Create crawler instance
        crawler = FirecrawlClient(api_key=settings.firecrawl_api_key)
        
        # Crawl the website
        pages = crawler.crawl_website(
            url=str(request.target_url),
            max_pages=request.max_pages,
            include_subdomains=request.include_subdomains
        )
        
        pages_crawled = len(pages) if pages else 0
        chunks_indexed = 0
        
        # Index the content
        if pages:
            result = retriever.indexer.index_multiple_pages(pages)
            chunks_indexed = result.get('chunks_indexed', 0)
        
        return CrawlResponse(
            success=True,
            pages_crawled=pages_crawled,
            chunks_indexed=chunks_indexed,
            message=f"Successfully crawled {pages_crawled} pages and indexed {chunks_indexed} content chunks."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to crawl website: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Get indexing statistics."""
    try:
        db_status = retriever.get_database_status()
        stats = retriever.indexer.get_collection_stats()
        
        return {
            "database_status": db_status["status"],
            "total_documents": db_status["total_documents"],
            "collection_name": stats["collection_name"],
            "embedding_model": stats["embedding_model"],
            "config": {
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "retrieval_k": settings.retrieval_k,
                "similarity_threshold": settings.similarity_threshold
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@app.delete("/clear")
async def clear_database():
    """Clear all indexed content."""
    try:
        success = retriever.indexer.clear_collection()
        
        if success:
            return {"message": "Database cleared successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear database"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear database: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
