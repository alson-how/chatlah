# RAG System - FastAPI + Firecrawl + Chroma

## Overview

This is a production-ready multi-tenant RAG system designed for merchant onboarding and configurable conversational AI with Google Calendar integration for automatic appointment scheduling. It integrates web crawling, content indexing, and intelligent business conversations. The system allows merchants to define custom information collection fields, conversation flows, and question templates, adapting to diverse industry requirements. It automatically crawls websites, processes and stores content in a vector database, and facilitates intelligent conversations via a FastAPI backend with an interactive admin dashboard. The project aims to provide adaptable and efficient lead generation, customer interaction, and automated appointment booking for various businesses.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- **GitHub Repository Setup**: Created comprehensive repository configuration with professional README, Docker deployment files, and authentication guides
- **Docker Deployment Package**: Production-ready containers with development and production configurations for Digital Ocean
- **Project Cleanup**: Streamlined codebase by removing unused files and organizing structure for deployment

## System Architecture

### Backend Framework
- **FastAPI Application**: Provides RESTful API with automatic documentation and CORS support.
- **Modular Design**: Organized into specialized modules for conversation flow, multi-field extraction, RAG, multi-tenant management, state definition, intent detection, and automated portfolio generation.
- **Session Management**: Utilizes a `ConversationState`-based architecture for persistent conversation tracking.

### Web Crawling Architecture
- **Firecrawl Integration**: Uses Firecrawl API for intelligent web crawling, extracting clean markdown and HTML content with metadata.
- **Content Filtering**: Focuses on main content while excluding scripts, styles, navigation, and footers.

### Content Processing Pipeline
- **Text Chunking**: Configurable chunk size (1000 characters) with overlap (200 characters) for context.
- **HTML Cleaning**: Uses BeautifulSoup for content extraction and normalization.
- **Text Normalization**: Regex-based cleaning for whitespace and special characters.

### Vector Database Architecture
- **ChromaDB Integration**: Persistent vector storage with configurable collection management.
- **OpenAI Embeddings**: Uses 'text-embedding-3-large' model for high-quality embedding generation.
- **Similarity Search**: Employs threshold-based filtering with configurable result limits.

### API Design
- **Core Endpoints**: Includes health checks, web crawling initiation, and question-answering with source citations.
- **Chat Endpoint**: Provides enhanced conversational AI with a Malaysian business tone, session management, and theme detection.
- **Merchant API Endpoints**: Supports merchant creation, configuration retrieval, template access, multi-tenant chat, and conversation history viewing.
- **Pydantic Models**: Used for request/response validation and API documentation.
- **Dynamic Tone System**: Configurable response styles loaded from external files.
- **Theme Detection**: Intelligent style/aesthetic query detection with portfolio URL mapping.

### User Interface Architecture
- **Admin Dashboard**: Comprehensive management interface with three main sections:
  - Website Crawling: For content management and indexing
  - Chatbot Fields: Custom field configuration for lead collection
  - Calendar Setup: Google OAuth2 integration for appointment scheduling
- **Enhanced Chatbot Interface**: Professional chat interface with a Malaysian business persona.
- **Merchant Setup Interface**: Comprehensive onboarding system with template selection, custom field builder (drag-and-drop, various field types), and conversation tone settings.
- **Responsive Design**: Mobile-friendly interfaces with modern UI components.
- **Advanced Features**: Dynamic multi-step conversation flows, configurable lead profile collection, conversation memory, greeting detection, query rewriting, portfolio integration, and intelligent progressive information gathering.

### Configuration Management
- **Environment-Based**: Centralized settings via `.env` files.
- **Configurable Parameters**: Chunk sizes, similarity thresholds, retrieval limits, and API keys.
- **Response Tone Configuration**: External text files for dynamic system prompt loading.

### Data Flow Architecture
- **Crawling to Indexing**: Firecrawl extracts content, which is cleaned, chunked, embedded using OpenAI, and stored in ChromaDB.
- **Conversation Management**: Session tracking via thread IDs and dynamic conversation state.
- **Progressive Lead Collection**: Multi-step information gathering for key details (name, phone, location, style) with advanced extraction (Malaysian location parser, style detection with RapidFuzz).
- **Conversation Flow Control**: Dynamic routing based on missing information requirements and completion detection.
- **Database Storage**: Lead profiles with location and style preferences stored persistently.
- **Response Generation**: Uses a Malaysian business tone with progressive questioning and completion confirmation.
- **Memory Update**: Conversation summarization for long-term context retention.

## External Dependencies

### Web Crawling Service
- **Firecrawl API**: Third-party service for intelligent website crawling and content extraction (requires `FIRECRAWL_API_KEY`).

### Vector Database
- **ChromaDB**: Open-source vector database for embedding storage and similarity search (local file-based persistent storage).

### Multi-Tenant Database Architecture
- **PostgreSQL**: Production database for persistent multi-tenant data management.
  - Tables: `merchants` (profiles, field configs), `conversation_sessions` (thread-based context), `consumer_data` (collected info).
  - Uses JSONB columns for flexible field configuration.
  - Requires standard PostgreSQL environment variables.

### Machine Learning Models
- **OpenAI Embeddings API**: Used for generating high-quality semantic embeddings with `text-embedding-3-large` model (requires `OPENAI_API_KEY`).

### Web Framework
- **FastAPI**: Main Python web framework.
- **Uvicorn**: ASGI server.
- **CORS Middleware**: For cross-origin resource sharing.

### Content Processing
- **BeautifulSoup4**: For HTML parsing and content extraction.
- **Pydantic**: For data validation and settings management.

### Database Management
- **psycopg2-binary**: PostgreSQL adapter for Python.

## Docker Deployment

### Container Configuration
- **Dockerfile**: Multi-stage build with Python 3.11-slim base image.
- **Health Checks**: Built-in health monitoring at `/health` endpoint.
- **Security**: Non-root user configuration and optimized dependencies.
- **Performance**: UV package manager for faster installs and production optimizations.

### Deployment Options
- **Development**: `docker-compose.yml` with local PostgreSQL database.
- **Production**: `docker-compose.prod.yml` for external managed database deployment.
- **Digital Ocean**: Comprehensive deployment guide with App Platform and Droplet instructions.

### Required Environment Variables
- Database: `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- APIs: `FIRECRAWL_API_KEY`, `OPENAI_API_KEY`
- OAuth: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- Domain: `DOMAIN`, `REPLIT_DEV_DOMAIN`