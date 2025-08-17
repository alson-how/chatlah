# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install UV for faster Python package management
RUN pip install uv

# Install Python dependencies
RUN uv pip install --system --no-cache -r pyproject.toml

# Install additional required packages not in pyproject.toml
RUN uv pip install --system --no-cache \
    fastapi \
    uvicorn[standard] \
    firecrawl-py \
    beautifulsoup4 \
    pydantic \
    python-multipart \
    psycopg2-binary \
    chromadb \
    openai \
    google-oauth2-tool \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    requests

# Copy application code
COPY . .

# Create data directory for ChromaDB
RUN mkdir -p /app/data/chroma

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Command to run the application
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]