# Local Development Setup

## Prerequisites

- **OS**: Windows, macOS, or Linux
- **Tools**: Git, Docker, Docker Compose, Python 3.11+
- **Port Availability**: 8000 (API), 8501 (Frontend)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Amith-Ganta/FastAPI-ML-EKS-Platform.git
cd FastAPI-ML-EKS-Platform
```

### 2. Setup with Docker Compose (Recommended)

This is the fastest way to get the full stack running:

```bash
# Build and start containers
docker-compose up --build

# In separate terminal, view logs
docker-compose logs -f

# Stop services
docker-compose down
```

The services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:8501

### 3. Setup Without Docker (Local Python)

If you prefer to run locally without Docker:

#### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run API server
uvicorn app:app --reload --port 8000

# Server runs at http://localhost:8000
```

#### Frontend Setup

In a new terminal:

```bash
# Navigate to frontend
cd frontend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run frontend.py --server.port 8501

# UI runs at http://localhost:8501
```

## Project Structure Reference

```
FastAPI-ML-EKS-Platform/
├── backend/
│   ├── app.py                    # FastAPI application
│   ├── model.pkl                 # Trained ML model
│   ├── Dockerfile                # Backend image config
│   └── requirements.txt           # Backend dependencies
│
├── frontend/
│   ├── frontend.py               # Streamlit UI
│   ├── Dockerfile.streamlit      # Frontend image config
│   └── requirements.txt           # Frontend dependencies
│
├── data/
│   ├── insurance.csv             # Training data
│   └── patients.json             # Sample data
│
├── docs/
│   ├── API.md                    # API documentation
│   ├── ARCHITECTURE.md           # System design
│   ├── LOCAL_SETUP.md            # This file
│   └── DEPLOYMENT.md             # Production deployment
│
├── docker-compose.yml            # Local orchestration
└── README.md                     # Project overview
```

## Common Tasks

### Run Tests

```bash
# Backend tests (if available)
cd backend
pytest

# Or with coverage
pytest --cov
```

### View API Documentation

Once the API is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Check Container Status

```bash
# List running containers
docker ps

# View container logs
docker logs fastapi-api        # Backend logs
docker logs streamlit-frontend # Frontend logs

# Follow logs in real-time
docker logs -f fastapi-api
```

### Rebuild Containers

```bash
# Full rebuild with fresh images
docker-compose up --build --force-recreate

# Or for a specific service
docker-compose up --build api   # Just backend
```

### Clean Up Docker

```bash
# Stop all containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Clean up unused images/containers
docker system prune -a --volumes
```

## Troubleshooting

### "Port already in use"

```bash
# Find process using port 8000
# On Windows (PowerShell):
Get-NetTCPConnection -LocalPort 8000 | Select-Object -Property OwningProcess

# Kill process (Windows):
taskkill /PID <PID> /F

# On macOS/Linux:
lsof -i :8000
kill -9 <PID>

# Or use Docker to clean up:
docker ps -a | grep -E "fastapi|streamlit" | awk '{print $1}' | xargs docker rm -f
```

### "Dependency not found"

```bash
# Reinstall requirements
cd backend && pip install --upgrade -r requirements.txt
cd frontend && pip install --upgrade -r requirements.txt
```

### "Model file not found"

Ensure `backend/model.pkl` exists. If missing:

```bash
# Check file exists
ls -la backend/model.pkl

# The file should be in git. If not:
git status
git lfs status  # If using Git LFS
```

### Frontend can't reach API

Check the API URL in `frontend/frontend.py`:

```python
# Should be:
API_URL = "http://localhost:8000/predict"  # For local development
# Or:
API_URL = "http://fastapi-api:8000/predict"  # Within Docker network
```

### Container crashes on startup

```bash
# Check logs for error details
docker-compose logs --tail=50

# Rebuild with verbose output
docker-compose up --build

# Check individual image build
docker build -f backend/Dockerfile ./backend
```

## Development Workflow

### Making Changes

1. **Edit code** in your editor
2. **For local Python**: Changes auto-reload (with `--reload`)
3. **For Docker**: Need to rebuild after changes

```bash
# Rebuild just the changed service
docker-compose up --build api    # If backend changed
docker-compose up --build frontend # If frontend changed
```

### Testing the API

Use the interactive Swagger UI:
1. Go to http://localhost:8000/docs
2. Find the `/predict` endpoint
3. Click "Try it out"
4. Enter sample values:
   - age: 35
   - weight: 70
   - height: 1.8
   - income_lpa: 15
   - smoker: false
   - city: Mumbai
   - occupation: private_job
5. Click "Execute"

Or use curl:

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 35,
    "weight": 70,
    "height": 1.8,
    "income_lpa": 15,
    "smoker": false,
    "city": "Mumbai",
    "occupation": "private_job"
  }'
```

## Environment Configuration

Local runs need no secrets. For cloud deployment, the pipeline reads its
credentials from **GitHub repository secrets** (see the secrets table in the
[README](../README.md#cicd-secrets) and [DEPLOYMENT.md](DEPLOYMENT.md)):

| Secret | Purpose |
|--------|---------|
| `DOCKER_USERNAME` / `DOCKER_TOKEN` | Docker Hub publish |
| `AWS_HOST` | EC2 public IP for SSH deploy |
| `AWS_SSH_KEY` | EC2 private key (PEM contents) |
| `AWS_USER` | EC2 SSH user *(optional, defaults to `ubuntu`)* |

For local tooling, copy [`config/.env.example`](../config/.env.example) to
`config/.env` and fill it in.

**Never commit `.env` files or private keys** — they contain secrets.

## Next Steps

- Read [API.md](API.md) for API endpoint documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Review main [README.md](../README.md) for project overview
