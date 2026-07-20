# System Architecture

## Overview

The Insurance Premium Predictor is an **image-first** ML microservice. The core
deliverable is a single, self-contained Docker image
(`tweakster24/insurance-premium-api:latest` — the validated image used
throughout the EKS deployment) that is verified by CI and run unchanged on any
host. An optional Streamlit UI is provided
as a separate client. The system favours a single immutable artifact over
environment-specific deployment scripts.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  (Code, CI/CD workflow, Secrets Management)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ [Push to main]
                     │
┌────────────────────▼────────────────────────────────────────┐
│              GitHub Actions CI/CD Pipeline                   │
│ Mirror upstream → smoke-test (/docs, /predict) → Push → Deploy│
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ [Publish verified image]
                     ▼
            ┌──────────────────┐
            │   Docker Hub     │
            │ insurance-       │
            │ premium-api      │
            │ :latest          │
            └────────┬─────────┘
                     │
                     │ [docker pull && docker run]
                     ▼
┌──────────────────────────────────────────────────────────────┐
│        Any host (laptop / VM / AWS EC2 / container PaaS)     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │   insurance-premium-api container  (Port 8000)       │    │
│  │   - app.py  (validation + feature engineering)       │    │
│  │   - model.pkl  (scikit-learn pipeline)               │    │
│  │   - /predict (REST + readiness/Swagger at /docs)     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Optional: Streamlit UI container (Port 8501) → calls :8000  │
└──────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer (Streamlit)

**Location:** `frontend/`

**Responsibilities:**
- User-friendly web interface
- Form input collection and validation
- Real-time prediction results display
- API communication handling

**Technology:**
- Streamlit 1.43.0 for rapid UI development
- Requests library for HTTP calls
- Python 3.11

**Environment:**
- Port: 8501
- Container: streamlit-frontend

### 2. Backend Layer (FastAPI)

**Location:** `backend/`

**Responsibilities:**
- REST API for predictions
- Input validation using Pydantic models
- Machine learning model inference
- Feature computation (BMI, age groups, city tiers)

**Technology:**
- FastAPI 0.115.12 for high-performance async APIs
- Uvicorn 0.34.2 as ASGI server
- Pydantic 2.11.4 for data validation
- Scikit-learn 1.6.1 for ML model
- Pandas 2.2.3 for data processing
- Python 3.11

**API Endpoints:**
- `GET /docs` - Interactive Swagger documentation (also the readiness probe)
- `GET /openapi.json` - OpenAPI specification
- `POST /predict` - Insurance category prediction (returns category + confidence + class probabilities)

**Environment:**
- Port: 8000
- Container: insurance-premium-api
- Published image: `tweakster24/insurance-premium-api:latest` (validated image used across the EKS deployment)

### 3. ML Model

**Type:** Classification model (Scikit-learn)

**Location:** `backend/model.pkl`

**Features Used:**
- BMI (calculated from height/weight)
- Age group (derived from age)
- Lifestyle risk (derived from smoker status and BMI)
- City tier (derived from city name)
- Income (LPA)
- Occupation

**Output:** Insurance premium category (discrete classification)

### 4. Data Layer

**Location:** `data/`

**Files:**
- `insurance.csv` - Training dataset
- `patients.json` - Sample patient data

### 5. Infrastructure Layer

**Containerization:**
- Docker containers for API and Frontend
- Docker Compose for multi-container orchestration
- `.dockerignore` for build optimization

**Deployment:**
- GitHub Actions pulls the validated image and smoke-tests the HTTP contract
- Docker Hub as the image registry (`tweakster24/insurance-premium-api`)
- CI auto-deploys to AWS EC2 (`204.236.207.23`) over SSH once secrets are set
- Deploy anywhere else via the same `docker pull && docker run`

## Data Flow

### 1. Prediction Request Flow

```
User Input (Frontend)
         │
         ▼
   [Streamlit UI]
         │
         ├─ Validate input
         │
         ▼
  [HTTP POST to API]
         │
         ├─ /predict endpoint
         │
         ▼
 [Pydantic Validation]
         │
         ├─ Compute derived features
         │  - BMI = weight / height²
         │  - Age group classification
         │  - Lifestyle risk assessment
         │  - City tier mapping
         │
         ▼
   [ML Model Inference]
         │
         ├─ Load model.pkl
         │
         ├─ Prepare feature vector
         │
         ├─ model.predict() + model.predict_proba()
         │
         ▼
  [JSON Response]
   { response: { predicted_category, confidence, class_probabilities } }
         │
         ▼
  [Client / Streamlit UI displays category + confidence]
```

### 2. Deployment Flow

```
Developer Push to GitHub (main branch)
         │
         ▼
GitHub Actions Triggered (deploy.yml)
         │
         ├─ [Pull]   validated tweakster24/insurance-premium-api:latest
         │
         ├─ [Run]    start the container
         │
         ├─ [Test]   smoke-test /docs and /predict (assert contract)
         │
         ├─ [Deploy] SSH → EC2: pull & run the image  (guarded by AWS secrets)
         │
         ▼
Live on http://204.236.207.23:8000  (Swagger at /docs)
```

## Security Considerations

### 1. Secrets Management

- GitHub Secrets store sensitive data:
  - `AWS_HOST`, `AWS_SSH_KEY`, `AWS_USER` - EC2 SSH deployment

- Secrets are never logged or exposed in CI/CD logs
- The EC2 deploy is guarded: if its secrets are absent, the pipeline still pulls
  and smoke-tests the image, then skips deployment (stays green)

### 2. Network Security

- EC2 security groups control inbound/outbound traffic
- API runs on private container network
- Public ports: 8000 (API), 8501 (Frontend)

### 3. Input Validation

- Pydantic models enforce strict type checking
- Field constraints (ranges, valid values)
- Automatic API documentation prevents misuse

## Scaling Considerations

### Current Limitations

- Single EC2 instance (t3.micro)
- No load balancing
- No auto-scaling
- No database (stateless predictions)

### Future Improvements

- Kubernetes cluster for multi-container orchestration
- Load balancer (ELB/ALB) for traffic distribution
- Auto-scaling groups for dynamic capacity
- Cache layer (Redis) for frequently predicted categories
- Database for audit/analytics
- CDN for static assets

## Development Workflow

```
Feature Branch
     │
     ├─ Local development with docker-compose
     │
     ├─ Test with http://localhost:8000/docs
     │
     ├─ Push to feature branch
     │
     ▼
Pull Request
     │
     ├─ Code review
     │
     ├─ CI checks (if configured)
     │
     ▼
Merge to main
     │
     ├─ Automatic GitHub Actions deployment
     │
     ├─ Containers updated on EC2
     │
     ▼
Live deployment
```

## Technology Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI | High performance, async support, auto OpenAPI docs |
| Streamlit | Rapid UI development, good for data apps, minimal code |
| Docker Compose | Local dev matches production, easy setup |
| GitHub Actions | Integrated with repository, free tier sufficient |
| Scikit-learn | Lightweight, good for tabular data classification |
| Pydantic | Strong type validation, OpenAPI integration |

## Monitoring & Logging

**Current:** Manual log inspection via `docker logs`

**Future Considerations:**
- CloudWatch for EC2 metrics
- ELK stack for centralized logging
- Prometheus + Grafana for monitoring
- Error tracking (Sentry)
- Performance monitoring (New Relic, DataDog)
