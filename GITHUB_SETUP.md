# GitHub Repository Setup Guide

This guide helps you create and configure your own GitHub repository for the RAG system.

## Step 1: Create GitHub Repository

1. **Go to GitHub** (https://github.com)
2. **Sign in** to your account (or create one if needed)
3. **Click "New repository"** (green button or + icon)
4. **Configure your repository:**
   - Repository name: `rag-system-interior-design` (or your preferred name)
   - Description: `AI-powered RAG system for interior design lead generation with Google Calendar integration`
   - Set to **Public** (recommended) or **Private**
   - **Do NOT** initialize with README, .gitignore, or license (we have these files)

## Step 2: Push Your Code to GitHub

Run these commands in your project directory:

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: RAG system with Docker deployment ready"

# Add your GitHub repository as remote (replace with your username and repo name)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Configure Repository Settings

### Add Repository Description
1. Go to your repository on GitHub
2. Click the gear icon next to "About"
3. Add description: "AI-powered RAG system for interior design lead generation with Google Calendar integration"
4. Add topics: `rag`, `fastapi`, `docker`, `interior-design`, `ai`, `chatbot`, `calendar-integration`

### Set up Repository Secrets (for GitHub Actions)
If you plan to use GitHub Actions for CI/CD:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `FIRECRAWL_API_KEY`: Your Firecrawl API key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `GOOGLE_OAUTH_CLIENT_ID`: Your Google OAuth client ID
   - `GOOGLE_OAUTH_CLIENT_SECRET`: Your Google OAuth client secret

## Step 4: Connect to Digital Ocean

### For Digital Ocean App Platform:
1. Go to Digital Ocean → Apps
2. Click "Create App"
3. Choose "GitHub" as source
4. Select your repository
5. Configure environment variables
6. Deploy

### For Digital Ocean Droplet:
```bash
# On your droplet
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

## Step 5: Set Up Development Workflow

### Clone for Local Development:
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### Make Changes and Push:
```bash
# Make your changes
git add .
git commit -m "Description of your changes"
git push origin main
```

## Repository Structure

Your repository will contain:
```
├── app/                     # Main application code
├── admin/                   # Admin dashboard
├── static/                  # Frontend interfaces
├── utils/                   # Utility functions
├── crawler/                 # Web crawling module
├── tone/                    # Response tone configurations
├── data/                    # Data storage (ChromaDB)
├── Dockerfile               # Docker container configuration
├── docker-compose.yml       # Development deployment
├── docker-compose.prod.yml  # Production deployment
├── deploy.sh               # Automated deployment script
├── DEPLOYMENT.md           # Deployment instructions
├── README.md               # Project documentation
├── pyproject.toml          # Python dependencies
└── .dockerignore           # Docker build optimization
```

## Best Practices

### Branch Protection
1. Go to **Settings** → **Branches**
2. Add rule for `main` branch
3. Enable "Require pull request reviews"
4. Enable "Require status checks"

### Issue Templates
Create `.github/ISSUE_TEMPLATE/` directory with:
- `bug_report.md`
- `feature_request.md`

### Contributing Guidelines
Add `CONTRIBUTING.md` with development guidelines

## Security Considerations

- **Never commit API keys** to the repository
- Use environment variables for all secrets
- Add `.env` to `.gitignore` (already included)
- Regular security audits with `npm audit` or similar tools

## Collaboration

### Add Collaborators:
1. Go to **Settings** → **Manage access**
2. Click "Invite a collaborator"
3. Enter GitHub username or email

### Fork and Pull Request Workflow:
1. Contributors fork your repository
2. Make changes in their fork
3. Create pull request to your main branch
4. Review and merge changes

Your RAG system is now ready for collaborative development and deployment!