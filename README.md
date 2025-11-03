# FastAPI Project with Docker and Nginx

A production-ready FastAPI application with Docker containerization and Nginx reverse proxy for cloud deployment.

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py
│   │           ├── companies.py
│   │           ├── employees.py
│   │           ├── password_reset.py
│   │           └── users.py
│   └── core/
│       ├── __init__.py
│       └── config.py         # Application settings
├── nginx/
│   └── nginx.conf            # Nginx configuration
├── Dockerfile                # FastAPI app Docker image
├── docker-compose.yml        # Docker Compose configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .dockerignore
└── README.md

```

## Features

- ✅ FastAPI with automatic OpenAPI documentation
- ✅ Docker containerization
- ✅ Nginx reverse proxy
- ✅ Production-ready configuration
- ✅ Health check endpoints
- ✅ CORS support
- ✅ Environment-based configuration

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- (Optional) Python 3.11+ for local development

### Using Docker Compose (Recommended)

1. **Clone and navigate to the project directory**

2. **Copy environment file** (optional):
   ```bash
   cp .env.example .env
   ```

3. **Build and start the services**:
   ```bash
   docker-compose up --build
   ```

4. **Access the application**:
   - API: http://localhost
   - API Documentation: http://localhost/api/v1/docs
   - Health Check: http://localhost/health

### Local Development

1. **Install UV**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the application**:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/v1/docs

## Docker Commands

### Build and run
```bash
docker-compose up --build
```

### Run in detached mode
```bash
docker-compose up -d
```

### View logs
```bash
docker-compose logs -f app
docker-compose logs -f nginx
```

### Stop services
```bash
docker-compose down
```

### Rebuild after changes
```bash
docker-compose up --build
```

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
PROJECT_NAME=FastAPI App
VERSION=1.0.0
API_V1_STR=/api/v1
BACKEND_CORS_ORIGINS=*
HOST=0.0.0.0
PORT=8000
```

### Nginx Configuration

The Nginx configuration is located in `nginx/nginx.conf`. It:
- Proxies requests to the FastAPI application
- Sets up security headers
- Configures proper forwarding headers
- Supports WebSockets

## Cloud Deployment

### Deploy to Cloud Platforms

#### AWS (EC2/ECS/Lightsail)
1. Push your code to a repository
2. Set up EC2 instance or ECS cluster
3. Install Docker and Docker Compose
4. Clone repository and run `docker-compose up -d`
5. Configure security groups to allow HTTP/HTTPS traffic

#### Google Cloud Platform (Cloud Run/Compute Engine)
1. Build and push Docker images to GCR
2. Use Cloud Run for serverless deployment or
3. Use Compute Engine with Docker Compose

#### Azure (Container Instances/App Service)
1. Build Docker image
2. Push to Azure Container Registry
3. Deploy to Azure Container Instances or App Service

#### DigitalOcean (App Platform/Droplets)
1. For App Platform: Connect GitHub repo and deploy
2. For Droplets: SSH in, install Docker, and run `docker-compose up -d`

#### Heroku
1. Use Heroku container registry
2. Deploy with `heroku container:push web` and `heroku container:release web`

### Production Considerations

1. **HTTPS/SSL**: Configure SSL certificates in Nginx
   - Add SSL configuration to `nginx/nginx.conf`
   - Mount certificates in `docker-compose.yml`

2. **Environment Variables**: Use secrets management:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Platform-specific secret stores

3. **Database**: Add a database service:
   ```yaml
   # Add to docker-compose.yml
   db:
     image: postgres:15-alpine
     environment:
       POSTGRES_DB: myapp
       POSTGRES_USER: user
       POSTGRES_PASSWORD: password
   ```

4. **Logging**: Configure log aggregation:
   - ELK Stack
   - CloudWatch (AWS)
   - Application Insights (Azure)

5. **Monitoring**: Add monitoring tools:
   - Prometheus + Grafana
   - New Relic
   - Datadog

6. **Scaling**: 
   - Use multiple app instances behind Nginx
   - Consider Kubernetes for orchestration
   - Use cloud load balancers

## Development

### Adding New Endpoints

1. Create endpoint file in `app/api/v1/endpoints/`
2. Add router to `app/api/v1/__init__.py`
3. Endpoint will be automatically available at `/api/v1/...`

### Testing

```bash
# Run tests (when implemented)
pytest

# With coverage
pytest --cov=app
```

## Troubleshooting

### Port already in use
```bash
# Change ports in docker-compose.yml
ports:
  - "8080:80"  # Use different host port
```

### Container won't start
```bash
# Check logs
docker-compose logs app

# Rebuild
docker-compose up --build --force-recreate
```

### Permission issues
```bash
# Fix permissions (Linux/Mac)
sudo chown -R $USER:$USER .
```

## License

MIT

