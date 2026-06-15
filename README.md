# Backend DevOps Assignment - CSV Transaction Processing Pipeline

A production-ready asynchronous CSV transaction processing pipeline built with **FastAPI**, **Celery**, **PostgreSQL**, and **Redis**. This project demonstrates best practices in data cleaning, anomaly detection, and LLM-powered summarization.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Scaling Considerations](#scaling-considerations)

---

## 🎯 Project Overview

This application processes CSV files containing transaction data asynchronously. It performs:

1. **Data Cleaning**: Deduplication, normalization, and schema validation
2. **Anomaly Detection**: Statistical and merchant-based anomaly flagging
3. **Category Classification**: LLM-powered missing category prediction
4. **Narrative Summarization**: Generates human-readable summaries of processed transactions

Users upload a CSV file via the REST API, and the system processes it in the background while providing real-time status updates.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Web Server                      │
│  • REST API Endpoints  • WebUI  • Static Files  • Health Checks │
└──────────────┬──────────────────────────────────────────────────┘
               │
       ┌───────┴────────┬──────────────────┐
       │                │                  │
   ┌───▼────┐      ┌────▼─────┐      ┌───▼───┐
   │Database │      │Redis     │      │Uploads│
   │         │      │          │      │       │
   │PostgreSQL      │Job Queue │      │Storage│
   │• Jobs      │      │Results  │      │Files │
   │• Results   │      │Session  │      │      │
   └───┬────┘      └────┬─────┘      └───────┘
       │                │
       └───────┬────────┘
               │
       ┌───────▼──────────────┐
       │  Celery Worker Pool  │
       │  • CSV Validation    │
       │  • Data Cleaning     │
       │  • Anomaly Detection │
       │  • LLM Integration   │
       │  • Result Storage    │
       └──────────────────────┘
```

### Data Flow

1. **Upload**: User uploads CSV via `POST /api/v1/jobs/upload`
2. **Queuing**: API validates file, stores on disk, creates job record, enqueues Celery task
3. **Processing**: Worker validates schema, removes duplicates, normalizes data
4. **Enrichment**: Anomaly detection and LLM-powered category classification
5. **Completion**: Results stored in database, job marked as complete
6. **Retrieval**: Client polls `/api/v1/jobs/{job_id}/status` and fetches `/api/v1/jobs/{job_id}/results`

---

## 🛠️ Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **API Framework** | FastAPI | 0.115.6 |
| **Server** | Uvicorn | 0.34.0 |
| **Database** | PostgreSQL | 16 |
| **ORM** | SQLAlchemy | 2.0.36 |
| **Task Queue** | Celery | 5.4.0 |
| **Message Broker** | Redis | 7 |
| **Testing** | Pytest | 8.3.4 |
| **Containerization** | Docker & Docker Compose | Latest |
| **Python** | 3.9+ | - |

---

## ✨ Features

- ✅ **Async Processing**: Non-blocking CSV processing with Celery workers
- ✅ **Data Validation**: Schema and integrity checks for CSV files
- ✅ **Automatic Cleaning**: Deduplication, normalization, and missing value handling
- ✅ **Anomaly Detection**: Statistical and merchant-based anomaly flagging
- ✅ **LLM Integration**: Supports Gemini, OpenAI, Ollama, and local heuristic fallback
- ✅ **Real-time Status**: WebUI and API polling for job progress
- ✅ **Error Handling**: Comprehensive error reporting with job failure tracking
- ✅ **REST API**: Complete OpenAPI documentation with interactive Swagger UI
- ✅ **Docker Support**: Full Docker Compose setup for local and production environments
- ✅ **Type Safety**: Full type hints with Pydantic validation

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.9+ (for local development)
- Git

### Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Backend_DevOps_Assignment
   ```

2. **Create environment file**
   ```bash
   cat > .env << EOF
   # Optional: Set to use external LLM providers
   # GEMINI_API_KEY=your_key_here
   # OPENAI_API_KEY=your_key_here
   # OLLAMA_BASE_URL=http://ollama:11434
   EOF
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - **WebUI**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health

5. **View logs**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f worker
   ```

### Local Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start services (PostgreSQL & Redis)**
   ```bash
   docker-compose up -d db redis
   ```

4. **Run migrations** (if applicable)
   ```bash
   # Handled automatically on startup via init_db()
   ```

5. **Start FastAPI server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Start Celery worker** (in another terminal)
   ```bash
   celery -A app.core.celery_app.celery_app worker --loglevel=INFO
   ```

---

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. **Upload CSV**
```http
POST /jobs/upload
Content-Type: multipart/form-data

curl -F "file=@sample_data/transactions.csv" http://localhost:8000/api/v1/jobs/upload
```

**Response (201 Created):**
```json
{
  "job_id": "3fe17e57-c223-4386-a7b7-8bfc509879f1",
  "status": "pending",
  "message": "Job accepted for processing."
}
```

---

#### 2. **Get Job Status**
```http
GET /jobs/{job_id}/status
```

**Example:**
```bash
curl http://localhost:8000/api/v1/jobs/3fe17e57-c223-4386-a7b7-8bfc509879f1/status
```

**Response:**
```json
{
  "job_id": "3fe17e57-c223-4386-a7b7-8bfc509879f1",
  "status": "completed",
  "message": "Job completed successfully.",
  "summary": "Processed 1,234 transactions..."
}
```

**Status Values:** `pending` | `processing` | `completed` | `failed`

---

#### 3. **Get Job Results**
```http
GET /jobs/{job_id}/results
```

**Example:**
```bash
curl http://localhost:8000/api/v1/jobs/3fe17e57-c223-4386-a7b7-8bfc509879f1/results
```

**Response:**
```json
{
  "job_id": "3fe17e57-c223-4386-a7b7-8bfc509879f1",
  "cleaned_transactions": [...],
  "anomalies": [...],
  "spend_by_category": {...},
  "summary": "..."
}
```

**Note:** Returns `409 Conflict` if job is not completed.

---

#### 4. **List Jobs**
```http
GET /jobs?status=completed
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "...",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z"
    }
  ]
}
```

**Query Parameters:**
- `status`: Filter by status (`pending`, `processing`, `completed`, `failed`)

---

### Interactive API Documentation

Swagger UI available at: **http://localhost:8000/docs**

---

## 📁 Project Structure

```
Backend_DevOps_Assignment/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── jobs.py                 # REST API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Settings & configuration
│   │   ├── database.py             # SQLAlchemy setup
│   │   └── celery_app.py           # Celery configuration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pipeline.py             # Main processing pipeline
│   │   ├── csv_parser.py           # CSV parsing & validation
│   │   ├── cleaner.py              # Data cleaning logic
│   │   ├── anomaly.py              # Anomaly detection
│   │   └── llm.py                  # LLM client (Gemini, OpenAI, Ollama)
│   ├── static/
│   │   └── index.html              # WebUI
│   ├── models.py                   # SQLAlchemy models
│   ├── schemas.py                  # Pydantic request/response schemas
│   ├── tasks.py                    # Celery tasks
│   └── main.py                     # FastAPI app initialization
├── tests/
│   └── test_pipeline_units.py      # Unit tests
├── docs/
│   ├── ARCHITECTURE.md             # Architecture documentation
│   ├── API.md                      # API reference
│   └── VIDEO_REVIEW_GUIDE.md       # Implementation review guide
├── docker-compose.yml              # Container orchestration
├── Dockerfile                      # Container image definition
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/transactions

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# LLM Configuration (optional)
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
OLLAMA_BASE_URL=http://localhost:11434

# Upload Configuration
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=52428800  # 50MB in bytes

# API Configuration
API_PREFIX=/api/v1
APP_NAME=Transaction Processing Pipeline
```

### Application Settings

Settings are managed in `app/core/config.py` using Pydantic Settings:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str
    database_url: str
    redis_url: str
    upload_dir: str
    # ... more settings
```

---

## 👨‍💻 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_pipeline_units.py

# Run with coverage
pytest --cov=app
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Adding New Features

1. **New API Endpoint**: Add to `app/api/jobs.py`
2. **New Processing Step**: Add to `app/services/pipeline.py`
3. **New Database Model**: Add to `app/models.py` and run migrations
4. **New Task**: Create in `app/tasks.py` and decorate with `@celery_app.task`

---

## 🔄 Processing Pipeline Details

### 1. CSV Validation
- Checks file extension (.csv)
- Validates file size (max 50MB)
- Validates schema (required columns)

### 2. Data Cleaning
- **Deduplication**: Removes exact duplicate rows
- **Date Normalization**: Parses multiple date formats
- **Amount Normalization**: Handles currency and decimal formatting
- **Status Normalization**: Standardizes transaction statuses
- **Currency Handling**: Validates currency codes

### 3. Anomaly Detection
- **Statistical Anomalies**: Outliers using IQR method
- **Merchant Anomalies**: Unusual merchant behavior
- **Category Anomalies**: Missing or incorrect categories

### 4. Category Classification
- Batch processes transactions with missing categories
- Uses LLM (Gemini, OpenAI, or Ollama) for intelligent classification
- Falls back to heuristic matching if no LLM configured

### 5. Summarization
- Generates narrative summary of transaction data
- Includes spend patterns, trends, and insights
- Stored for UI display and archival

---

## 📊 Scaling Considerations

As traffic grows, these components will become bottlenecks:

1. **Disk I/O**: Move uploads to object storage (AWS S3, Google Cloud Storage)
2. **Database**: Increase connection pool size, enable read replicas
3. **Worker Concurrency**: Use multiple worker processes on dedicated machines
4. **Redis Memory**: Monitor queue depth, implement backpressure
5. **LLM Rate Limits**: Implement request queuing and provider-specific rate limiting
6. **Idempotency**: Add request idempotency keys for at-least-once semantics

**Production Recommendations:**
- Use managed database service (AWS RDS, Google Cloud SQL)
- Use managed Redis (AWS ElastiCache, Google Cloud Memorystore)
- Deploy workers on Kubernetes with auto-scaling
- Add structured logging (ELK, Datadog, New Relic)
- Implement distributed tracing (Jaeger, Lightstep)
- Use API gateway with rate limiting and monitoring

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check if ports are in use
lsof -i :8000
lsof -i :5432
lsof -i :6379

# View detailed logs
docker-compose logs api
docker-compose logs worker
docker-compose logs db
```

### Worker Not Processing Jobs

```bash
# Verify Celery worker is running
docker-compose logs worker

# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Restart worker
docker-compose restart worker
```

### Database Connection Issues

```bash
# Verify database is healthy
docker-compose exec db pg_isready -U postgres

# Check database logs
docker-compose logs db

# Access database directly
docker-compose exec db psql -U postgres -d transactions
```

### LLM Integration Issues

- Verify API keys are set correctly in `.env`
- Check LLM provider status page
- Review logs for rate limiting errors
- Ensure network connectivity to LLM endpoints

---
## 📝 Author

Najiya Khatoon

Aspiring AI/ML & Backend Developer

GitHub:
https://github.com/khatoonnajiyaf438-cell


## 📝 License

This project is part of a backend/DevOps assignment and is provided as-is.

---

## 📧 Support

For issues, questions, or improvements, please refer to the documentation in the `docs/` directory or review the API documentation at http://localhost:8000/docs.

---

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

---


**Project Status**: ✅ Active Development



