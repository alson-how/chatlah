#!/bin/bash

# Simple deployment script for RAG System

echo "🚀 RAG System Docker Deployment Script"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Check for environment file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating template..."
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://postgres:password@db:5432/ragdb
PGHOST=db
PGPORT=5432
PGUSER=postgres
PGPASSWORD=password
PGDATABASE=ragdb

# API Keys (REQUIRED - Replace with your actual keys)
FIRECRAWL_API_KEY=your-firecrawl-api-key-here
OPENAI_API_KEY=your-openai-api-key-here

# Google OAuth (Optional - for calendar integration)
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret

# Domain Configuration
DOMAIN=localhost:5000
REPLIT_DEV_DOMAIN=localhost:5000

# Security
FLASK_SECRET_KEY=your-random-secret-key-here
EOF
    echo "📝 Created .env template file. Please edit it with your actual API keys before running again."
    echo "Required: FIRECRAWL_API_KEY and OPENAI_API_KEY"
    exit 1
fi

echo "✅ Environment file found"

# Prompt for production or development deployment
echo ""
echo "Select deployment type:"
echo "1) Development (with local PostgreSQL)"
echo "2) Production (external database)"
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        COMPOSE_FILE="docker-compose.yml"
        echo "🔧 Using development configuration with local database"
        ;;
    2)
        COMPOSE_FILE="docker-compose.prod.yml"
        echo "🏭 Using production configuration"
        echo "⚠️  Make sure your DATABASE_URL points to your production database"
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "🔨 Building Docker image..."
docker build -t rag-system:latest .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed. Please check the logs above."
    exit 1
fi

echo "✅ Docker image built successfully"

echo ""
echo "🚀 Starting services..."
docker-compose -f $COMPOSE_FILE up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "📊 Service Status:"
    docker-compose -f $COMPOSE_FILE ps
    echo ""
    echo "🌐 Your RAG system is now running at:"
    echo "   • Main Interface: http://localhost:5000"
    echo "   • Chat Interface: http://localhost:5000/chat"
    echo "   • Admin Dashboard: http://localhost:5000/admin"
    echo "   • API Documentation: http://localhost:5000/docs"
    echo "   • Health Check: http://localhost:5000/health"
    echo ""
    echo "📋 Useful commands:"
    echo "   • View logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "   • Stop services: docker-compose -f $COMPOSE_FILE down"
    echo "   • Restart: docker-compose -f $COMPOSE_FILE restart"
    echo ""
    echo "🔍 If you encounter issues, check the logs and ensure all API keys are correctly set in .env"
else
    echo "❌ Deployment failed. Check the logs with: docker-compose -f $COMPOSE_FILE logs"
    exit 1
fi