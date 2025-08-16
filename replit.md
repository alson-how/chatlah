# RAG System - FastAPI + Firecrawl + Chroma

## Overview

This is a production-ready Retrieval Augmented Generation (RAG) system that combines web crawling, content indexing, and advanced conversational AI capabilities. The system automatically crawls websites using the Firecrawl API, processes and chunks the content, stores it in ChromaDB for vector search, and provides intelligent business conversations through both a FastAPI backend and an interactive chat interface. The architecture features conversation memory, query rewriting, Malaysian business tone, and real-time chat flow to ensure professional, context-aware customer interactions.

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
- **Ask Endpoint**: Question-answering with source citations, confidence scoring, and configurable response tone
- **Chat Endpoint**: Enhanced conversational AI with Malaysian business tone, session management, and theme detection
- **Request/Response Models**: Pydantic models for validation and API documentation
- **Dynamic Tone System**: Configurable response styles (customer_support, technical, casual) loaded from external files
- **Theme Detection**: Intelligent style/aesthetic query detection with portfolio URL mapping

### User Interface Architecture
- **Web Crawler Interface**: Main page for website crawling and content management
- **Enhanced Chatbot Interface**: Professional chat interface with Malaysian business persona
- **Conversation Management**: Thread-based sessions with clear conversation history
- **Responsive Design**: Mobile-friendly interfaces with modern UI components
- **Cross-Navigation**: Seamless navigation between crawler and chat interfaces
- **Advanced Features**: Dynamic multi-step conversation flow, complete lead profile collection (name, contact, location, style), conversation memory, greeting detection, query rewriting, portfolio integration, and intelligent progressive information gathering

### Configuration Management
- **Environment-Based**: Centralized settings with .env file support
- **API Keys**: Secure handling of Firecrawl and OpenAI API credentials
- **Configurable Parameters**: Chunk sizes, similarity thresholds, and retrieval limits
- **Response Tone Configuration**: External tone files (customer_support.txt, technical.txt, casual.txt) for dynamic system prompt loading

### Data Flow Architecture
1. **Crawling**: Firecrawl API extracts website content with proper URL extraction from metadata
2. **Processing**: Content is cleaned, chunked, and embedded using OpenAI text-embedding-3-large
3. **Indexing**: Vectors and metadata stored in ChromaDB with authentic page URLs
4. **Conversation Management**: Session tracking with thread IDs and dynamic conversation state
5. **Progressive Lead Collection**: Multi-step information gathering for name, phone, location, and style preferences
6. **Advanced Information Extraction**: Malaysian location parser with fuzzy matching, building detection, and comprehensive location aliases (KL, PJ, Mont Kiara, etc.)
7. **Smart Style Detection**: Advanced style parsing with canonical themes, portfolio links, and typo tolerance using RapidFuzz
8. **Conversation Flow Control**: Dynamic routing based on missing information requirements
9. **Completion Detection**: Only ends conversation when all required data (name, phone, location, style) is collected
10. **Database Storage**: Complete lead profiles with location and style preference tracking
11. **Response Generation**: Malaysian business tone with progressive question flow and completion confirmation
12. **Memory Update**: Conversation summarization for long-term context retention

## External Dependencies

### Web Crawling Service
- **Firecrawl API**: Third-party service for intelligent website crawling and content extraction
- **API Key Authentication**: Requires FIRECRAWL_API_KEY environment variable

### Vector Database
- **ChromaDB**: Open-source vector database for embedding storage and similarity search
- **Persistent Storage**: Local file-based storage in configurable directory path

### Lead Database
- **PostgreSQL**: Production database for persistent lead storage and management
- **Tables**: leads table with comprehensive contact tracking, theme interests, and timestamps
- **Environment Variables**: DATABASE_URL, PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE

### Lead Database
- **PostgreSQL**: Production database for persistent lead storage and management
- **Tables**: leads table with comprehensive contact tracking, theme interests, and timestamps
- **Environment Variables**: DATABASE_URL, PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE

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

### Database Management
- **psycopg2-binary**: PostgreSQL adapter for Python database operations
- **Lead Management**: Automated contact collection with persistent storage

### Required Integrations
- **OpenAI API**: Primary embedding service (requires OPENAI_API_KEY)
- **Environment Variables**: .env file support for configuration management