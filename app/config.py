"""Configuration management for the RAG system."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 5000
    
    # Firecrawl Configuration
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
    
    # OpenAI Configuration (for embeddings fallback)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Chroma Configuration
    chroma_db_path: str = "./data/chroma"
    chroma_collection_name: str = "website_content"
    
    # Embedding Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Chunking Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Retrieval Configuration
    retrieval_k: int = 5
    similarity_threshold: float = 0.7
    
    # Target website to crawl
    target_website: str = os.getenv("TARGET_WEBSITE", "")
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()

# Legacy constants for backward compatibility
FIRECRAWL_API_KEY = settings.firecrawl_api_key
OPENAI_API_KEY = settings.openai_api_key
CHROMA_DIR = settings.chroma_db_path
COLLECTION_NAME = settings.chroma_collection_name
