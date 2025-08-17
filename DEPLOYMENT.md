# Docker Deployment Guide for Digital Ocean

This guide helps you deploy your RAG system to Digital Ocean using Docker containers.

## Prerequisites

Before deploying, ensure you have:

1. **Digital Ocean Account** with billing enabled
2. **Domain name** (optional but recommended)
3. **API Keys** for:
   - Firecrawl API
   - OpenAI API
   - Google OAuth (for calendar integration)

## Step 1: Prepare Your Environment Variables

You'll need these environment variables for production:

### Required Database Variables
```bash
DATABASE_URL=postgresql://username:password@host:5432/database_name
PGHOST=your-postgres-host
PGPORT=5432
PGUSER=your-username
PGPASSWORD=your-password
PGDATABASE=your-database-name
```

### Required API Keys
```bash
FIRECRAWL_API_KEY=your-firecrawl-api-key
OPENAI_API_KEY=your-openai-api-key
```

### Google Calendar Integration (Optional)
```bash
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
```

### Domain Configuration
```bash
DOMAIN=your-domain.com
REPLIT_DEV_DOMAIN=your-domain.com
```

## Step 2: Deploy to Digital Ocean

### Option A: Using Digital Ocean App Platform (Recommended)

1. **Create a new App in Digital Ocean**
   ```bash
   # Push your code to GitHub first
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/your-repo.git
   git push -u origin main
   ```

2. **Configure the App**
   - Connect your GitHub repository
   - Select the `Dockerfile` build method
   - Set environment variables in the App Platform dashboard
   - Configure domain settings if you have one

3. **Database Setup**
   - Add a PostgreSQL managed database
   - Copy the connection string to your environment variables

### Option B: Using Digital Ocean Droplets

1. **Create a Droplet**
   ```bash
   # Select Ubuntu 22.04 LTS
   # Choose appropriate size (minimum 2GB RAM recommended)
   # Add your SSH key
   ```

2. **Install Docker on the Droplet**
   ```bash
   ssh root@your-droplet-ip
   
   # Update system
   apt update && apt upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Install Docker Compose
   apt install docker-compose -y
   
   # Start Docker
   systemctl start docker
   systemctl enable docker
   ```

3. **Deploy Your Application**
   ```bash
   # Clone your repository
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
   
   # Create environment file
   nano .env
   # Add all your environment variables here
   
   # Start the application
   docker-compose up -d
   ```

## Step 3: Configure Google OAuth (If Using Calendar)

1. **Go to Google Cloud Console**
   - Visit https://console.cloud.google.com/apis/credentials
   - Create a new OAuth 2.0 Client ID
   - Add your domain to Authorized redirect URIs:
     ```
     https://your-domain.com/google_login/callback
     ```

2. **Update Environment Variables**
   - Add your Google OAuth credentials to your deployment

## Step 4: Set Up Database

Your application will automatically create the necessary database tables on first run.

## Step 5: Configure Reverse Proxy (For Droplet Deployment)

If using a droplet, set up Nginx as a reverse proxy:

```bash
# Install Nginx
apt install nginx -y

# Create configuration
nano /etc/nginx/sites-available/rag-system

# Add this configuration:
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Enable the site
ln -s /etc/nginx/sites-available/rag-system /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## Step 6: Set Up SSL (Optional but Recommended)

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate
certbot --nginx -d your-domain.com

# Auto-renewal
crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Health Monitoring

Your application includes a health check endpoint at `/health` that monitors:
- Application status
- Database connectivity
- Service availability

## Scaling Considerations

For production use, consider:

1. **Database**: Use Digital Ocean Managed PostgreSQL
2. **File Storage**: Configure persistent volumes for ChromaDB data
3. **Load Balancing**: Use multiple app instances behind a load balancer
4. **Monitoring**: Set up logging and monitoring
5. **Backups**: Configure automated database backups

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify DATABASE_URL is correct
   - Check firewall settings
   - Ensure database is accessible

2. **API Key Issues**
   - Verify all required API keys are set
   - Check API key permissions and quotas

3. **Memory Issues**
   - Ensure sufficient RAM (minimum 2GB)
   - Monitor ChromaDB storage usage

### Logs

View application logs:
```bash
# Using Docker Compose
docker-compose logs -f app

# Using Docker directly
docker logs -f container-name
```

## Cost Optimization

- Start with a $10-20/month droplet for testing
- Use managed database for production reliability
- Monitor usage and scale as needed
- Consider using Digital Ocean's App Platform for automatic scaling

## Support

For deployment issues:
1. Check the application logs
2. Verify all environment variables are set
3. Test database connectivity
4. Ensure all required API keys are valid

Your RAG system is now ready for production deployment on Digital Ocean!