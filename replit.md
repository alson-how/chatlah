# RAG System - FastAPI + Firecrawl + Chroma

## Overview

This is a production-ready Retrieval Augmented Generation (RAG) system that combines web crawling, content indexing, and question-answering capabilities. The system automatically crawls websites using the Firecrawl API, processes and chunks the content, stores it in ChromaDB for vector search, and provides grounded Q&A responses through a FastAPI backend. The architecture supports semantic search with citation support and similarity scoring to ensure reliable, source-backed responses.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **FastAPI Application**: RESTful API with automatic documentation and CORS middleware
- **Modular Design**: Clean separation of concerns with dedicated modules for crawling, indexing, retrieval, and API endpoints
- **Exception Handling**: Centralized error handling with structured error responses

### Web Crawling Architecture
- **Firecrawl Integration**: External API service for intelligent website crawling
- **Single Page Scraping**: Extracts clean markdown and HTML content with metadata
- **Content Filtering**: Excludes scripts, styles, navigation, and footer elements while focusing on main content
- **Pipeline Automation**: Complete crawling and indexing pipeline with configuration validation

### Content Processing Pipeline
- **Text Chunking**: Configurable chunk size (1000 characters) with overlap (200 characters) for context preservation
- **HTML Cleaning**: BeautifulSoup-based content extraction and normalization
- **Text Normalization**: Regex-based cleaning for whitespace and special character handling

### Vector Database Architecture
- **ChromaDB Integration**: Persistent vector storage with configurable collection management
- **OpenAI Embeddings**: Uses 'text-embedding-3-large' model for high-quality embedding generation
- **Similarity Search**: Threshold-based filtering with configurable result limits
- **Metadata Storage**: URL, title, and content metadata for citation support

### API Design
- **Health Endpoint**: System status monitoring with database connectivity checks
- **Crawl Endpoint**: Website crawling with configurable parameters (max pages, subdomain inclusion)
- **Ask Endpoint**: Question-answering with source citations and confidence scoring
- **Request/Response Models**: Pydantic models for validation and API documentation

### Configuration Management
- **Environment-Based**: Centralized settings with .env file support
- **API Keys**: Secure handling of Firecrawl and OpenAI API credentials
- **Configurable Parameters**: Chunk sizes, similarity thresholds, and retrieval limits

### Data Flow Architecture
1. **Crawling**: Firecrawl API extracts website content
2. **Processing**: Content is cleaned, chunked, and embedded
3. **Indexing**: Vectors and metadata stored in ChromaDB
4. **Retrieval**: Semantic search finds relevant content chunks
5. **Response**: Grounded answers with source citations and similarity scores

## External Dependencies

### Web Crawling Service
- **Firecrawl API**: Third-party service for intelligent website crawling and content extraction
- **API Key Authentication**: Requires FIRECRAWL_API_KEY environment variable

### Vector Database
- **ChromaDB**: Open-source vector database for embedding storage and similarity search
- **Persistent Storage**: Local file-based storage in configurable directory path

### Machine Learning Models
- **OpenAI Embeddings API**: Advanced text embedding generation service
- **Model**: text-embedding-3-large for high-quality semantic embeddings (3072 dimensions)

### Web Framework
- **FastAPI**: Modern Python web framework with automatic API documentation
- **Uvicorn**: ASGI server for running the FastAPI application
- **CORS Middleware**: Cross-origin resource sharing support

### Content Processing
- **BeautifulSoup4**: HTML parsing and content extraction
- **Pydantic**: Data validation and settings management

### Required Integrations
- **OpenAI API**: Primary embedding service (requires OPENAI_API_KEY)
- **Environment Variables**: .env file support for configuration management