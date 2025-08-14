# RAG System - FastAPI + Firecrawl + Chroma

A production-ready Retrieval Augmented Generation (RAG) system that automatically crawls websites using Firecrawl, indexes content in ChromaDB, and provides grounded Q&A responses through a FastAPI interface.

## Features

- **🕷️ Web Crawling**: Automated website crawling using Firecrawl API
- **📚 Content Indexing**: Intelligent text chunking and vector embedding storage with ChromaDB
- **🤖 Q&A System**: Semantic search and grounded response generation
- **🔍 Citation Support**: Responses include source citations with similarity scores
- **⚡ FastAPI Backend**: RESTful API with automatic documentation
- **🏗️ Modular Architecture**: Clean, maintainable, and extensible codebase

## Quick Start

### 1. Installation

```bash
# Clone or create project directory
mkdir rag-site && cd rag-site

# Install dependencies
pip install -r requirements.txt
