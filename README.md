# 🏠 RAG System - AI Interior Design Assistant

A sophisticated conversational AI system for interior design lead generation and appointment scheduling, leveraging Retrieval-Augmented Generation (RAG) to provide intelligent, context-aware interactions.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow?logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?logo=postgresql)](https://www.postgresql.org/)

## 🚀 Key Features

- **🧠 Advanced RAG Implementation**: Uses Firecrawl for web crawling and ChromaDB for vector storage
- **💬 Intelligent Conversation Management**: Multi-step lead collection with dynamic conversation flows
- **🤖 Machine Learning Integration**: OpenAI embeddings and GPT models for natural conversations
- **📅 Appointment Scheduling**: Google Calendar OAuth2 integration for automatic booking
- **🏢 Multi-tenant Architecture**: Supports multiple merchants with custom configurations
- **🎛️ Admin Dashboard**: Comprehensive interface for website management, field configuration, and calendar setup
- **🚀 Production Ready**: Docker deployment with health monitoring and scalability considerations

## 🛠️ Technology Stack

- **Backend**: FastAPI with Python 3.11+
- **Vector Database**: ChromaDB for semantic search
- **Web Crawling**: Firecrawl API for intelligent content extraction
- **Database**: PostgreSQL for persistent data management
- **ML Models**: OpenAI GPT and embedding models
- **Calendar**: Google Calendar API integration
- **Deployment**: Docker with Digital Ocean support

## 📋 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- API keys for Firecrawl and OpenAI
- PostgreSQL database (local or managed)

### 🐳 Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database settings
   ```

3. **Deploy with Docker**
   ```bash
   # Development (with local database)
   docker-compose up -d
   
   # Production (with external database)
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Access the application**
   - Main Interface: http://localhost:5000
   - Admin Dashboard: http://localhost:5000/admin
   - API Documentation: http://localhost:5000/docs

### 💻 Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # or
   uv pip install -r pyproject.toml
   ```

2. **Start the development server**
   ```bash
   python -m uvicorn app.api:app --host 0.0.0.0 --port 5000 --reload
   ```

## 🌐 Deployment

### Digital Ocean App Platform
1. Connect your GitHub repository
2. Configure environment variables
3. Deploy automatically

### Digital Ocean Droplets
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 📁 Project Structure

```
├── app/                     # Main application code
│   ├── api.py              # FastAPI main application
│   ├── database.py         # Database operations
│   ├── models.py           # Pydantic models
│   └── ...                 # Other modules
├── admin/                   # Admin dashboard
├── static/                  # Frontend interfaces
├── utils/                   # Utility functions
├── crawler/                 # Web crawling module
├── tone/                    # Response tone configurations
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Development deployment
├── docker-compose.prod.yml # Production deployment
└── DEPLOYMENT.md           # Deployment guide
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://username:password@host:5432/database
PGHOST=your-postgres-host
PGUSER=your-username
PGPASSWORD=your-password
PGDATABASE=your-database

# API Keys
FIRECRAWL_API_KEY=your-firecrawl-key
OPENAI_API_KEY=your-openai-key

# Google OAuth (Optional)
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret

# Domain
DOMAIN=your-domain.com
```

## 🎯 Features in Detail

### Intelligent Conversation Flow
- Progressive information collection (name, phone, location, style preferences)
- Dynamic conversation routing based on user responses
- Memory management for long conversations
- Intent detection and appropriate responses

### Admin Dashboard
- **Website Crawling**: Add and manage content sources
- **Field Configuration**: Customize lead collection fields
- **Calendar Setup**: Connect Google Calendar for appointment booking

### Multi-tenant Support
- Merchant-specific configurations
- Custom conversation flows per business
- Isolated data and settings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Deployment Guide](DEPLOYMENT.md)
- 📖 [GitHub Setup Guide](GITHUB_SETUP.md)
- 🐛 [Report Issues](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/issues)

## 🏗️ Architecture

The system follows a modular architecture with:
- **FastAPI backend** for API endpoints and business logic
- **ChromaDB** for vector storage and semantic search
- **PostgreSQL** for persistent data and multi-tenant management
- **Google Calendar API** for appointment scheduling
- **Docker** for containerization and deployment

Built with scalability and maintainability in mind, suitable for production deployment on Digital Ocean or other cloud platforms.