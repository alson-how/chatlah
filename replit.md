# RAG System - FastAPI + Firecrawl + Chroma

## Overview

This is a production-ready multi-tenant RAG system with merchant onboarding capabilities. The system combines web crawling, content indexing, and configurable conversational AI that adapts to different merchant requirements across various industries. Merchants can configure custom information collection fields, conversation flows, and question templates. The system automatically crawls websites using the Firecrawl API, processes and chunks the content, stores it in ChromaDB for vector search, and provides intelligent business conversations through both a FastAPI backend and an interactive merchant setup interface.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (August 17, 2025)

✅ **Budget Field Integration & Location Parsing Bug Fix - COMPLETED**:
- **Fixed Critical Location Parsing**: Resolved issue where "I'm looking for ID for my condo" incorrectly tagged "ID" as location instead of recognizing it as Interior Design intent
- **Added Budget Field**: Integrated budget field into ConversationState dataclass with complete extraction logic
- **Budget Extraction Patterns**: Implemented regex patterns for "50k", "RM 100k", "allocated 50k", "budget 75k" formats
- **Enhanced Field Tracking**: Updated field dictionaries and default configurations to include budget as required field
- **Complete Flow Verified**: Tested full conversation from "ID for condo" query through all required fields (name, phone, style, location, budget) to appointment scheduling
- **TESTING CONFIRMED**: Location parser no longer creates false positives, budget extraction works correctly, appointment scheduling triggers properly
- **PRODUCTION READY**: All dynamic fields working correctly with robust conversation management and automatic completion detection

✅ **Enhanced Checklist System & Code Modularization - COMPLETED**:
- **Intelligent Checklist Management**: Implemented comprehensive checklist system that tracks all required fields (name, phone, style, location, budget)
- **Smart Question Rotation**: Added cooldown mechanism (2-turn minimum) to prevent asking same field repeatedly, with intelligent rotation to different questions
- **Always Follow-up After Portfolio**: Fixed the issue where chatbot stopped after portfolio response - now always asks next missing field
- **Progress Tracking**: Enhanced conversation state with field ask counts, last asked tracking, and completion progress monitoring
- **Modular Architecture**: Extracted intent detection (`app/intents.py`) and slot management (`app/slots.py`) from main API file
- **RAG Integration with Continuation**: Answers side questions (pricing, process) while maintaining conversation flow to collect missing information
- **Dynamic Field Configuration**: Integrated with admin dashboard to support customizable required fields and question texts
- **Enhanced Response Format**: API now returns detailed checklist status, missing fields, and completion progress for better monitoring
- **TESTING CONFIRMED**: Portfolio responses include follow-up questions, conversation continues until all fields captured, smart question rotation working
- **PRODUCTION READY**: Robust conversation management ensures no lead information is missed, natural user experience with persistent data collection

✅ **Complete Admin Dashboard with Dynamic Field Configuration - COMPLETED**:
- Created comprehensive admin dashboard with PostgreSQL database backend (`admin/admin_database.py`)
- Built professional admin interface with crawl website home page (`admin/templates/admin_dashboard.html`) 
- Added dynamic chatbot fields configuration page (`admin/templates/admin_fields.html`) with full CRUD operations
- Implemented RESTful API endpoints (`admin/admin_api.py`) for field management:
  - `GET /admin`: Main dashboard with website crawling interface
  - `GET /admin/fields`: Field configuration page with add/edit/delete functionality
  - `POST /admin/api/fields`: Create new custom fields
  - `PUT /admin/api/fields/{id}`: Update field configurations
  - `DELETE /admin/api/fields/{id}`: Remove fields
- Enhanced conversation controller to use dynamic field configs from database (line 717 area in `app/api.py`)
- Added `get_dynamic_field_configs()`, `dynamic_next_slot()`, and `is_ready_for_appointment_dynamic()` functions
- **TESTING CONFIRMED**: Admin can customize information collection fields and chatbot adapts automatically
- **PRODUCTION READY**: Complete admin dashboard with dynamic field management and automatic appointment scheduling

✅ **Enhanced API Optimization with Dynamic Architecture - COMPLETED**:
- Implemented enhanced slot-driven conversation model with `EnhancedConversationState` dataclass
- Added sophisticated phone ask policy with cooldown and rotating prompts to prevent loops
- Enhanced RAG integration with `rag_answer_one_liner()` and improved portfolio preview
- Added `enhanced_handle_turn()` controller with intelligent conversation flow management
- Created `/ask_enhanced` endpoint with comprehensive state tracking and completion progress
- **TESTING CONFIRMED**: Portfolio queries, multi-field extraction, and smart conversation routing all working
- **PRODUCTION READY**: Enhanced system provides natural conversation flow with better user experience

✅ **Automatic Appointment Scheduling Integration - COMPLETED**:
- Added dynamic appointment readiness detection based on admin field configuration
- Implemented automatic appointment scheduling when all required fields are collected
- Added variety of appointment scheduling messages with personalized details formatting
- Enhanced conversation flow to seamlessly transition from lead collection to appointment booking
- **TESTING CONFIRMED**: System automatically proceeds to appointment scheduling after collecting required fields
- **USER PREFERENCE**: System dynamically adjusts required fields and proceeds to appointment when complete

## System Architecture

### Backend Framework
- **FastAPI Application**: RESTful API with automatic documentation and CORS middleware
- **Modular Design**: Clean separation of concerns with specialized conversation modules:
  - `controller.py`: Main conversation flow orchestration
  - `late_capture.py`: Multi-field information extraction
  - `rag_assist.py`: Enhanced intelligent question answering with intent detection
  - `optimized_chat.py`: Multi-tenant conversation management
  - `slots.py`: Conversation state and field definitions
  - `intents.py`: Intent detection for portfolio, pricing, consultation, and services
  - `portfolio_preview.py`: Automated portfolio example generation
- **Exception Handling**: Centralized error handling with structured error responses
- **Session Management**: ConversationState-based architecture with persistent storage

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
- **Merchant API Endpoints**: Complete merchant onboarding and configuration management
  - `POST /api/v1/merchants`: Create new merchant with custom field configuration
  - `GET /api/v1/merchants/{id}`: Retrieve merchant configuration
  - `GET /api/v1/templates`: Get pre-built industry templates
  - `POST /api/v1/chat`: Multi-tenant chat with merchant-specific flows
  - `GET /api/v1/merchants/{id}/conversations`: View merchant conversation history
- **Request/Response Models**: Pydantic models for validation and API documentation
- **Dynamic Tone System**: Configurable response styles (customer_support, technical, casual) loaded from external files
- **Theme Detection**: Intelligent style/aesthetic query detection with portfolio URL mapping

### User Interface Architecture
- **Web Crawler Interface**: Main page for website crawling and content management
- **Enhanced Chatbot Interface**: Professional chat interface with Malaysian business persona
- **Merchant Setup Interface**: Comprehensive onboarding system for merchant configuration
  - Template selection (Interior Design, Real Estate, Restaurant, Fitness)
  - Custom field builder with drag-and-drop interface
  - Field type configuration (Name, Phone, Email, Location, Style, Choice, Number, Text)
  - Conversation tone settings (Professional, Friendly, Casual)
- **Conversation Management**: Thread-based sessions with clear conversation history
- **Responsive Design**: Mobile-friendly interfaces with modern UI components
- **Cross-Navigation**: Seamless navigation between crawler, chat, and merchant setup interfaces
- **Advanced Features**: Dynamic multi-step conversation flow, configurable lead profile collection, conversation memory, greeting detection, query rewriting, portfolio integration, and intelligent progressive information gathering

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

### Multi-Tenant Database Architecture
- **PostgreSQL**: Production database for persistent multi-tenant data management
- **Merchant Configuration Tables**:
  - `merchants`: Stores merchant profiles, field configurations, and conversation tones
  - `conversation_sessions`: Thread-based session management with merchant-specific context
  - `consumer_data`: Collected consumer information with merchant associations
- **Legacy Compatibility**: Backward-compatible lead tables for existing Jablanc Interior workflows
- **Environment Variables**: DATABASE_URL, PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
- **JSON Field Storage**: JSONB columns for flexible field configuration and collected data storage

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