# ComplianceGuard AI 🛡️

**Intelligent Document Processing & Compliance Analysis Platform**

A production-ready system for processing cybersecurity compliance documents with AI-powered text extraction and structured data storage. Built with modern Python best practices, this platform automatically extracts, chunks, and indexes documents for compliance analysis.

---

## 🎯 What It Does

ComplianceGuard AI provides a complete document processing pipeline:

1. **Document Upload**: Accept PDF and DOCX files via REST API
2. **Intelligent Extraction**: Process documents using Landing AI's Advanced Document Extraction
3. **Structured Storage**: Store documents, chunks, and metadata in PostgreSQL
4. **Cloud Integration**: Seamlessly upload files to AWS S3 with presigned URL access
5. **Query & Analysis**: Retrieve documents with rich filtering and chunk-level granularity

---

## ✨ Key Features

### Document Processing
- **Multi-format Support**: PDF and DOCX document processing
- **AI-Powered Extraction**: Landing AI ADE for accurate text extraction with 98% confidence
- **Chunk-Level Indexing**: Store document chunks with bounding boxes and page numbers
- **Section Detection**: Automatically identify document sections and splits
- **Deduplication**: SHA-256 hash-based duplicate detection

### Architecture
- **Modern Async Python**: Built with FastAPI and async SQLAlchemy 2.0
- **Containerized Deployment**: Complete Docker Compose orchestration
- **Automatic Migrations**: Database schema migrations run on startup
- **Cloud-Native Storage**: AWS S3 integration with credential chain support
- **Graceful Degradation**: System remains operational even if extraction fails

### Developer Experience
- **OpenAPI Documentation**: Interactive API docs at `/docs`
- **Type Safety**: Full Pydantic validation and SQLAlchemy type hints
- **Hot Reload**: Development mode with automatic code reloading
- **Health Checks**: Built-in container health monitoring

---

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have:

- **Docker Desktop** (version 20.10+) with Docker Compose V2
- **AWS Account** with S3 access configured locally (`~/.aws/credentials`)
- **Landing AI API Key** from [landing.ai](https://landing.ai/)
- **Python 3.13+** (for local development only)

### One-Command Deployment

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd complianceguard

# 2. Configure environment variables
cp .env.example .env
# Edit .env and add your Landing AI API key and S3 bucket name

# 3. Start the entire stack
docker compose -f docker-compose.dev.yml up -d
```

That's it! The system will:
- ✅ Start PostgreSQL database
- ✅ Run all database migrations automatically
- ✅ Start the FastAPI web server
- ✅ Connect to AWS S3 using your local credentials

Access the application at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Database**: localhost:5433 (PostgreSQL)

---

## 📋 Detailed Setup Guide

### Step 1: Environment Configuration

Create a `.env` file in the project root:

```bash
# Application Settings
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
SECRET_KEY=dev-secret-key-change-this-in-production-min-32-chars

# Database (Docker internal networking)
DATABASE_URL=postgresql://complianceguard:devpassword123@postgres:5432/complianceguard

# AWS S3 Storage
# Credentials are loaded automatically from ~/.aws/credentials
S3_BUCKET_NAME=your-bucket-name-here
S3_REGION=us-east-1

# Landing AI Configuration
LANDING_AI_API_KEY=your-landing-ai-api-key-here
LANDING_AI_BASE_URL=https://api.va.landing.ai/v1
LANDING_AI_TIMEOUT_SECONDS=120
LANDING_AI_MAX_RETRIES=3
```

**Important Notes:**
- AWS credentials are **automatically loaded** from your `~/.aws/credentials` file
- The S3 bucket must exist before starting the system
- Landing AI API key is required for document extraction

### Step 2: AWS S3 Setup

ComplianceGuard uses the AWS credential chain for authentication:

```bash
# Option 1: Use existing AWS CLI configuration
aws configure
# Enter your AWS Access Key ID and Secret Access Key

# Option 2: Set environment variables (optional)
export AWS_ACCESS_KEY_ID=your-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-key

# Create your S3 bucket
aws s3 mb s3://your-bucket-name --region us-east-1
```

The Docker container automatically mounts your `~/.aws` directory for seamless credential access.

### Step 3: Start the System

```bash
# Development mode with hot reload
docker compose -f docker-compose.dev.yml up -d

# View logs in real-time
docker compose -f docker-compose.dev.yml logs -f

# Check service status
docker compose -f docker-compose.dev.yml ps
```

**What Happens on Startup:**

1. **PostgreSQL Initialization** (10-15 seconds)
   - Creates database user and schema
   - Runs health checks

2. **Web Service Startup** (5-10 seconds)
   - Waits for PostgreSQL to be healthy
   - Runs database migrations (`alembic upgrade head`)
   - Starts FastAPI server with hot reload

3. **Ready for Requests**
   - API available at http://localhost:8000
   - Interactive documentation at http://localhost:8000/docs

### Step 4: Verify Installation

```bash
# Test API health
curl http://localhost:8000/api/v1/documents

# Expected response:
# {"items": [], "total": 0, "limit": 20, "offset": 0, "has_more": false}

# Upload a test document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/test.pdf" \
  -F "doc_type=ciso_report" \
  -F "doc_category=Test" \
  -F "uploaded_by_email=test@example.com"
```

---

## 🏗️ Architecture Overview

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.115+ | High-performance async REST API |
| **Database** | PostgreSQL 15 | Relational data with JSONB support |
| **ORM** | SQLAlchemy 2.0 | Modern async database access |
| **Validation** | Pydantic V2 | Request/response validation |
| **Document Processing** | Landing AI ADE | AI-powered text extraction |
| **Object Storage** | AWS S3 | Scalable document storage |
| **Containerization** | Docker Compose | Local development orchestration |
| **Migrations** | Alembic | Database version control |

### System Flow

```
┌─────────────┐
│   Client    │
│  (Browser/  │
│   API Tool) │
└──────┬──────┘
       │ HTTP/JSON
       ▼
┌─────────────────────────────────┐
│     FastAPI Application         │
│  ┌──────────────────────────┐  │
│  │  Document Upload API     │  │
│  └────────┬─────────────────┘  │
│           │                     │
│           ▼                     │
│  ┌──────────────────────────┐  │
│  │  S3 File Storage         │◄─┼─── AWS S3
│  │  (SHA-256 hash naming)   │  │
│  └────────┬─────────────────┘  │
│           │                     │
│           ▼                     │
│  ┌──────────────────────────┐  │
│  │  Landing AI Integration  │◄─┼─── Landing AI API
│  │  - Text Extraction       │  │
│  │  - Chunk Detection       │  │
│  │  - Section Splitting     │  │
│  └────────┬─────────────────┘  │
│           │                     │
│           ▼                     │
│  ┌──────────────────────────┐  │
│  │  PostgreSQL Storage      │  │
│  │  - Documents (full text) │  │
│  │  - Chunks (with bbox)    │◄─┼─── PostgreSQL
│  │  - Splits (sections)     │  │
│  └──────────────────────────┘  │
└─────────────────────────────────┘
```

### Database Schema

**documents** - Core document storage
- `id` (UUID): Primary key
- `file_name`, `file_path`, `file_hash`: File metadata
- `extracted_text` (TEXT): Full extracted document text
- `extraction_metadata` (JSONB): Processing metadata
- `extraction_status`: `pending` | `processing` | `completed` | `failed`

**document_chunks** - Granular content chunks
- `id` (UUID): Primary key
- `document_id` (FK): Parent document
- `chunk_type`: `text` | `table` | `figure` | `header`
- `content` (TEXT): Chunk markdown content
- `bounding_box` (JSONB): Page coordinates
- `page_number`, `chunk_order`: Position metadata

**document_splits** - Document sections
- `id` (UUID): Primary key
- `document_id` (FK): Parent document
- `identifier`: Section name (e.g., "Item_1C", "Risk_Factors")
- `chunk_ids` (ARRAY): References to constituent chunks
- `markdown` (TEXT): Combined section content

**Indexes for Performance:**
- Unique index on `file_hash` for deduplication
- GIN index on `extraction_metadata` for JSON queries
- Composite indexes on `(doc_type, extraction_status)`

---

## 📖 API Reference

### Document Upload

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Parameters:
  - file: binary (required) - PDF or DOCX file
  - doc_type: string (required) - Document type (ciso_report, sec_filing)
  - doc_category: string (optional) - Category tag
  - uploaded_by_email: string (optional) - Uploader email
  - uploaded_by_name: string (optional) - Uploader name

Response: 201 Created
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "incident_report.pdf",
  "doc_type": "ciso_report",
  "file_size_bytes": 2457600,
  "extraction_status": "completed",
  "file_url": "https://bucket.s3.amazonaws.com/...",
  "created_at": "2025-11-08T14:32:00Z"
}
```

### List Documents

```http
GET /api/v1/documents?doc_type=ciso_report&limit=20&offset=0

Response: 200 OK
{
  "items": [...],
  "total": 157,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

### Get Document Details

```http
GET /api/v1/documents/{document_id}

Response: 200 OK
{
  "id": "550e8400-...",
  "file_name": "report.pdf",
  "extracted_text": "Full document text...",
  "extraction_metadata": {
    "num_pages": 12,
    "num_chunks": 45,
    "chunk_types": {"text": 30, "table": 12, "figure": 3},
    "processing_time_ms": 4807,
    "confidence_score": 0.98,
    "model_version": "dpt-2-20250919"
  }
}
```

### Get Document Chunks

```http
GET /api/v1/documents/{document_id}/chunks

Response: 200 OK
{
  "items": [
    {
      "id": "650e8400-...",
      "chunk_type": "table",
      "content": "| Header | Value |\n|---|---|\n| Data | 123 |",
      "page_number": 3,
      "chunk_order": 5,
      "bounding_box": {
        "left": 100, "top": 200,
        "right": 500, "bottom": 300
      }
    }
  ],
  "total": 45
}
```

### Retry Failed Extraction

```http
POST /api/v1/documents/{document_id}/retry-extraction

Response: 200 OK
{
  "id": "550e8400-...",
  "extraction_status": "completed",
  "extracted_text": "Successfully extracted text..."
}
```

---

## 🛠️ Development Guide

### Local Development (Without Docker)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -e .

# 3. Start PostgreSQL (using Docker)
docker compose -f docker-compose.dev.yml up postgres -d

# 4. Update .env with localhost database
DATABASE_URL=postgresql://complianceguard:devpassword123@localhost:5433/complianceguard

# 5. Run migrations
alembic upgrade head

# 6. Start development server
uvicorn complianceguard.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=complianceguard --cov-report=html

# Run specific test file
pytest tests/test_documents.py -v
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

---

## 🐳 Docker Commands Reference

### Starting & Stopping

```bash
# Start all services in background
docker compose -f docker-compose.dev.yml up -d

# Start with log output
docker compose -f docker-compose.dev.yml up

# Stop all services
docker compose -f docker-compose.dev.yml down

# Stop and remove volumes (⚠️ deletes all data)
docker compose -f docker-compose.dev.yml down -v
```

### Viewing Logs

```bash
# Follow all logs
docker compose -f docker-compose.dev.yml logs -f

# View specific service
docker compose -f docker-compose.dev.yml logs -f web

# Last 100 lines
docker compose -f docker-compose.dev.yml logs --tail=100
```

### Rebuilding

```bash
# Rebuild after code changes
docker compose -f docker-compose.dev.yml build

# Rebuild without cache
docker compose -f docker-compose.dev.yml build --no-cache

# Rebuild and restart
docker compose -f docker-compose.dev.yml up -d --build
```

### Database Access

```bash
# Open PostgreSQL shell
docker exec -it complianceguard-postgres psql -U complianceguard -d complianceguard

# Run SQL query directly
docker exec complianceguard-postgres psql -U complianceguard -d complianceguard -c "SELECT COUNT(*) FROM documents;"

# Backup database
docker exec complianceguard-postgres pg_dump -U complianceguard complianceguard > backup.sql

# Restore database
docker exec -i complianceguard-postgres psql -U complianceguard complianceguard < backup.sql
```

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Application environment |
| `DEBUG` | No | `True` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `SECRET_KEY` | Yes | - | Secret key for sessions (32+ chars) |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `S3_BUCKET_NAME` | Yes | - | AWS S3 bucket name |
| `S3_REGION` | No | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | No | - | AWS access key (or use ~/.aws) |
| `AWS_SECRET_ACCESS_KEY` | No | - | AWS secret key (or use ~/.aws) |
| `LANDING_AI_API_KEY` | Yes | - | Landing AI API key |
| `LANDING_AI_BASE_URL` | No | `https://api.va.landing.ai/v1` | Landing AI endpoint |
| `LANDING_AI_TIMEOUT_SECONDS` | No | `120` | API timeout |
| `LANDING_AI_MAX_RETRIES` | No | `3` | Retry attempts |

### Document Processing Settings

```python
# Maximum file size (configured in code)
MAX_FILE_SIZE_MB = 50

# Allowed file extensions
ALLOWED_EXTENSIONS = [".pdf", ".docx"]

# Extraction timeout
EXTRACTION_TIMEOUT_SECONDS = 120
```

---

## 🚨 Troubleshooting

### Common Issues

**Problem**: Database connection refused
```bash
# Solution: Check PostgreSQL is running
docker compose -f docker-compose.dev.yml ps

# Restart PostgreSQL
docker compose -f docker-compose.dev.yml restart postgres
```

**Problem**: Landing AI 401 Unauthorized
```bash
# Solution: Verify API key in .env
cat .env | grep LANDING_AI_API_KEY

# Restart web service to reload environment
docker compose -f docker-compose.dev.yml restart web
```

**Problem**: S3 upload failed
```bash
# Solution: Check AWS credentials
aws s3 ls s3://your-bucket-name

# Verify bucket exists
aws s3 mb s3://your-bucket-name --region us-east-1

# Check mounted credentials
docker exec complianceguard-web cat /root/.aws/credentials
```

**Problem**: Migrations not running
```bash
# Solution: Run migrations manually
docker exec complianceguard-web alembic upgrade head

# Check migration status
docker exec complianceguard-web alembic current
```

### Debug Mode

Enable detailed logging:

```bash
# In .env
DEBUG=True
LOG_LEVEL=DEBUG

# Restart services
docker compose -f docker-compose.dev.yml restart
```

---

## 📊 Monitoring & Observability

### Health Checks

The web container includes health checks:

```bash
# Check container health
docker inspect complianceguard-web | grep -A 10 Health

# Manual health check
curl http://localhost:8000/api/v1/documents
```

### Metrics

```bash
# View container stats
docker stats complianceguard-web complianceguard-postgres

# Check database size
docker exec complianceguard-postgres psql -U complianceguard -d complianceguard -c "
  SELECT pg_size_pretty(pg_database_size('complianceguard'));
"

# Document statistics
curl http://localhost:8000/api/v1/documents | jq '.total'
```

---

## 🔒 Security Best Practices

### Implemented Safeguards

✅ **Input Validation**
- Pydantic schemas validate all API inputs
- File type and size restrictions enforced
- SQL injection prevention via SQLAlchemy ORM

✅ **Secure Storage**
- Documents stored in S3 with hash-based naming
- Presigned URLs with 24-hour expiration
- AWS credential chain (never hardcode keys)

✅ **Error Handling**
- Graceful degradation on service failures
- No sensitive data in error messages
- Comprehensive exception logging

### Production Checklist

Before deploying to production:

- [ ] Generate strong `SECRET_KEY` (32+ random characters)
- [ ] Set `DEBUG=False` and `ENVIRONMENT=production`
- [ ] Use AWS IAM roles instead of access keys
- [ ] Enable S3 bucket encryption and versioning
- [ ] Implement API rate limiting
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Enable PostgreSQL SSL connections
- [ ] Set up automated backups
- [ ] Implement monitoring and alerting

---

## 📈 Performance Optimization

### Current Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Document Upload | <2s | For 1MB PDF to S3 |
| Landing AI Extraction | 4-6s | Per document, 98% accuracy |
| Chunk Storage | <1s | Insert 50 chunks to PostgreSQL |
| API Response Time | <200ms | List/filter endpoints |
| Concurrent Uploads | 10+ | Limited by Landing AI rate limits |

### Scaling Recommendations

**For Higher Throughput:**
1. Add Redis caching layer for frequent queries
2. Implement background task queue (Celery) for extraction
3. Use read replicas for PostgreSQL
4. Enable S3 Transfer Acceleration
5. Deploy multiple web container instances with load balancer

**For Larger Documents:**
1. Increase `LANDING_AI_TIMEOUT_SECONDS`
2. Implement chunked S3 uploads (multipart)
3. Add document preprocessing (split large PDFs)

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with clear, descriptive commits
4. **Add tests** for new functionality
5. **Run quality checks**: `ruff format . && ruff check . && pytest`
6. **Push to your fork**: `git push origin feature/amazing-feature`
7. **Open a Pull Request** with a clear description

### Development Standards

- Follow PEP 8 style guide (enforced by Ruff)
- Add type hints to all functions
- Write docstrings for public APIs
- Maintain test coverage above 80%
- Update documentation for user-facing changes

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - High-performance Python web framework
- **Landing AI** - Advanced document extraction technology
- **SQLAlchemy** - Excellent async ORM capabilities
- **PostgreSQL** - Reliable, powerful database
- **Anthropic Claude** - AI assistance in development

---

**Built with modern Python best practices and a focus on simplicity, reliability, and developer experience.**

For questions or support, please open an issue on GitHub.
