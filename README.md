# ComplianceGuard AI

> Document ingestion and semantic search powered by ColPali vision-language embeddings

A FastAPI-based system for ingesting PDF documents, generating multi-vector embeddings, and performing semantic search. Documents are indexed using ColPali embeddings (via Modal), stored in Milvus vector database, with metadata in PostgreSQL and files in S3.

---

## Quick Start

### Prerequisites

- Docker Desktop with Docker Compose V2
- AWS credentials configured (`~/.aws/credentials` or environment variables)
- Modal API endpoint for ColPali embeddings

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd complianceguard

# Copy environment template
cp .env.example .env
```

Edit `.env` and set:
```bash
# Required: Your S3 bucket names
S3_BUCKET_NAME=your-documents-bucket
INDEXING_S3_BUCKET_NAME=your-page-images-bucket

# Required: Modal endpoint for embeddings
INDEXING_MODAL_URL=https://your-modal-endpoint.modal.run/get_embeddings
```

### 2. Start Services

```bash
docker compose -f docker-compose.dev.yml up -d
```

This starts:
- PostgreSQL (port 5433)
- Milvus vector database (port 19530)
- Supporting services (etcd, MinIO)
- FastAPI application (port 8000)

Wait ~30 seconds for all services to become healthy.

### 3. Verify Installation

```bash
# Check all services are running
docker compose -f docker-compose.dev.yml ps

# Test API
curl http://localhost:8000/api/v1/documents
```

✅ You're ready! API is at http://localhost:8000

---

## API Documentation

### Interactive Documentation

Open in your browser:

- **Swagger UI**: http://localhost:8000/docs
  - Interactive API testing
  - Try out endpoints directly
  - See request/response examples

- **OpenAPI JSON**: http://localhost:8000/openapi.json
  - Raw OpenAPI 3.0 specification
  - Import into Postman/Insomnia

---

## Using the APIs

### 1. Ingest Documents

Upload and index PDF documents:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "files=@document.pdf" \
  -F 'doc_types=["contract"]' \
  -F 'doc_categories=["legal"]' \
  -F 'metadata_list=[{"author": "John Doe"}]'
```

**Parameters:**
- `files` - One or more PDF files (required)
- `doc_types` - JSON array of document types (optional, matches files order)
- `doc_categories` - JSON array of categories (optional)
- `metadata_list` - JSON array of metadata objects (optional)

**Response:**
```json
{
  "total": 1,
  "successful": 1,
  "failed": 0,
  "duplicates": 0,
  "results": [
    {
      "filename": "document.pdf",
      "success": true,
      "duplicate": false,
      "document": {
        "id": "uuid-here",
        "filename": "document.pdf",
        "file_hash": "sha256-hash",
        "indexing_status": "completed",
        "num_pages_indexed": 5,
        "created_at": "2025-11-10T12:00:00Z"
      }
    }
  ]
}
```

**What happens:**
1. PDF uploaded to S3
2. Database record created
3. PDF converted to page images
4. Page images uploaded to S3
5. ColPali embeddings generated
6. Vectors stored in Milvus
7. Status updated to `completed`

⏱️ **Performance:** ~5 seconds per page (24s for 5-page document)

### 2. Search Documents

Semantic search across indexed documents:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the payment terms?",
    "k": 5,
    "min_threshold": 0.5
  }'
```

**Parameters:**
- `query` - Natural language search query (required)
- `k` - Number of results to return (1-50, default: 5)
- `min_threshold` - Minimum similarity score (0.0-1.0, default: 0.0)
- `index_name` - Milvus collection to search (optional)

**Response:**
```json
{
  "query": "What are the payment terms?",
  "k": 5,
  "min_threshold": 0.5,
  "index_name": "ingested_documents",
  "total_documents_in_index": 10,
  "results_count": 3,
  "results": [
    {
      "rank": 1,
      "score": 0.847,
      "page_number": 3,
      "filepath": "contract.pdf#page=3",
      "filename": "contract.pdf",
      "page_image_url": "https://s3.amazonaws.com/...",
      "document_id": "uuid-here",
      "doc_type": "contract",
      "doc_category": "legal",
      "metadata": {"author": "John Doe"}
    }
  ]
}
```

**Scores:** Higher is better (0.0-1.0). Typical good matches are >0.5.

### 3. List Documents

Get all ingested documents:

```bash
curl http://localhost:8000/api/v1/documents
```

**Response:**
```json
[
  {
    "id": "uuid-here",
    "filename": "document.pdf",
    "file_hash": "sha256-hash",
    "file_size_mb": 2.4,
    "doc_type": "contract",
    "indexing_status": "completed",
    "num_pages_indexed": 5,
    "created_at": "2025-11-10T12:00:00Z"
  }
]
```

### 4. Get Document Details

```bash
curl http://localhost:8000/api/v1/documents/{document_id}
```

---

## Common Workflows

### Batch Upload Multiple Files

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "files=@contract1.pdf" \
  -F "files=@contract2.pdf" \
  -F "files=@invoice.pdf" \
  -F 'doc_types=["contract","contract","invoice"]' \
  -F 'doc_categories=["legal","legal","finance"]'
```

### Search with Filters

```bash
# Only search within specific index
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "revenue projections",
    "k": 10,
    "min_threshold": 0.6,
    "index_name": "financial_docs"
  }'
```

### Check Indexing Status

```bash
# Get document by ID
curl http://localhost:8000/api/v1/documents/{document_id}

# Check indexing_status field:
# - "processing" = currently being indexed
# - "completed" = ready for search
# - "failed" = indexing error occurred
```

---

## Local Development Setup

### Without Docker

For development with hot reload:

```bash
# 1. Install Python 3.13+
python --version

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Install system dependencies (for PDF conversion)
# macOS:
brew install poppler

# Ubuntu/Debian:
sudo apt-get install poppler-utils

# 5. Start only database services
docker compose -f docker-compose.dev.yml up -d postgres etcd minio milvus

# 6. Update .env for local development
DATABASE_URL=postgresql://complianceguard:devpassword123@127.0.0.1:5433/complianceguard
INDEXING_MILVUS_URI=http://127.0.0.1:19530

# 7. Run migrations
alembic upgrade head

# 8. Start FastAPI with hot reload
uvicorn complianceguard.main:app --reload --host 0.0.0.0 --port 8000
```

Now code changes auto-reload without rebuilding Docker images.

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest

# With coverage
pytest --cov=complianceguard
```

---

## Docker Commands

### Start/Stop

```bash
# Start all services
docker compose -f docker-compose.dev.yml up -d

# Stop all services
docker compose -f docker-compose.dev.yml down

# Stop and delete all data (⚠️ destructive)
docker compose -f docker-compose.dev.yml down -v
```

### View Logs

```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.dev.yml logs -f web

# Last 50 lines
docker compose -f docker-compose.dev.yml logs --tail=50 web
```

### Restart Services

```bash
# Restart web after code changes
docker compose -f docker-compose.dev.yml restart web

# Restart all
docker compose -f docker-compose.dev.yml restart
```

### Database Access

```bash
# Open PostgreSQL shell
docker exec -it complianceguard-postgres psql -U complianceguard -d complianceguard

# Run SQL query
docker exec -it complianceguard-postgres psql -U complianceguard -d complianceguard \
  -c "SELECT filename, indexing_status FROM ingested_documents;"

# View all documents
docker exec -it complianceguard-postgres psql -U complianceguard -d complianceguard \
  -c "SELECT COUNT(*) FROM ingested_documents;"
```

---

## Configuration

### Environment Variables

Required variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# S3 Storage
S3_BUCKET_NAME=your-documents-bucket
S3_REGION=us-east-1
INDEXING_S3_BUCKET_NAME=your-page-images-bucket

# Embeddings Service
INDEXING_MODAL_URL=https://your-endpoint.modal.run/get_embeddings

# Milvus
INDEXING_MILVUS_URI=http://milvus:19530
INDEXING_DEFAULT_COLLECTION=ingested_documents
```

Optional variables:

```bash
# Application
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# AWS Credentials (if not using ~/.aws/credentials)
S3_ACCESS_KEY_ID=your-key-id
S3_SECRET_ACCESS_KEY=your-secret-key

# Indexing Settings
INDEXING_EMBEDDING_DIM=128
INDEXING_TRACKER_FILE=./artifacts/index_tracker.json
```

### AWS Credentials

The system uses AWS credential chain (in order):
1. Environment variables (`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file (automatically mounted in Docker)
3. IAM role (in production)

### S3 Buckets

Create two S3 buckets:

```bash
# Documents bucket (stores original PDFs)
aws s3 mb s3://your-documents-bucket --region us-east-1

# Page images bucket (stores extracted page PNGs)
aws s3 mb s3://your-page-images-bucket --region us-east-1
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service status
docker compose -f docker-compose.dev.yml ps

# View error logs
docker compose -f docker-compose.dev.yml logs web

# Restart from scratch
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL is healthy
docker compose -f docker-compose.dev.yml ps postgres

# Test connection
docker exec -it complianceguard-postgres psql -U complianceguard -d complianceguard -c "SELECT 1;"
```

### Milvus Connection Issues

```bash
# Check Milvus is healthy
docker compose -f docker-compose.dev.yml ps milvus

# Restart Milvus and dependencies
docker compose -f docker-compose.dev.yml restart etcd minio milvus
```

### Indexing Fails

```bash
# Check web logs for errors
docker compose -f docker-compose.dev.yml logs --tail=100 web

# Common issues:
# 1. Modal endpoint not responding
# 2. S3 upload permissions
# 3. Milvus collection not loaded

# Reset Milvus data
docker compose -f docker-compose.dev.yml stop milvus
docker volume rm boring_milvus-data
docker compose -f docker-compose.dev.yml up -d milvus
```

### Query Returns No Results

```bash
# Check if documents are indexed
curl http://localhost:8000/api/v1/documents

# Verify indexing_status is "completed"
# If "processing", wait and check again
# If "failed", check logs

# Try broader query with lower threshold
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "document", "k": 10, "min_threshold": 0.0}'
```

---

## Performance

### Current Metrics

- **Ingestion**: ~5 seconds per page (parallelized operations)
- **Query**: <2 seconds for 1000+ documents
- **Concurrent requests**: 10+ (limited by Modal rate limits)

### Optimization

The system uses:
- Async HTTP for Modal API calls (httpx)
- Thread pools for blocking operations (PDF conversion, Milvus)
- Parallel S3 uploads (asyncio.gather)
- Milvus MaxSim scoring for accurate ranking

### Monitoring

```bash
# Check container resource usage
docker stats complianceguard-web complianceguard-milvus complianceguard-postgres

# Database size
docker exec complianceguard-postgres psql -U complianceguard -d complianceguard \
  -c "SELECT pg_size_pretty(pg_database_size('complianceguard'));"

# Document count
curl http://localhost:8000/api/v1/documents | jq 'length'
```

---

## Project Structure

```
complianceguard/
├── src/complianceguard/
│   ├── api/v1/           # API endpoints
│   │   ├── ingest.py     # Document upload & indexing
│   │   └── query.py      # Semantic search
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── crud/             # Database operations
│   ├── indexing/         # ColPali + Milvus
│   │   ├── milvus_index.py      # Main indexing logic
│   │   ├── milvus_retriever.py  # Vector search
│   │   └── page_storage.py      # S3 operations
│   ├── utils/            # Utilities
│   └── config.py         # Configuration
├── migrations/           # Alembic migrations
├── docker-compose.dev.yml
├── Dockerfile
├── .env
└── README.md
```

---

## Migration Guide

### From Other Systems

If migrating from another document system:

1. **Export documents** to PDF format
2. **Batch upload** using the ingest API
3. **Verify indexing** completed successfully
4. **Test queries** to validate search quality

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Security

### Best Practices

✅ Never commit `.env` file
✅ Use IAM roles in production (not access keys)
✅ Enable S3 bucket encryption
✅ Use strong `SECRET_KEY` (32+ characters)
✅ Set `DEBUG=False` in production
✅ Enable HTTPS/TLS
✅ Implement rate limiting

### Production Checklist

- [ ] Change default database password
- [ ] Generate secure `SECRET_KEY`
- [ ] Set `ENVIRONMENT=production`
- [ ] Use AWS IAM roles
- [ ] Enable S3 encryption
- [ ] Configure firewall rules
- [ ] Set up SSL certificates
- [ ] Enable database backups
- [ ] Implement monitoring/alerting

---

## License

MIT License - see LICENSE file for details

---

## Support

For issues, questions, or contributions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Search existing GitHub issues
3. Open a new issue with:
   - Error logs
   - Steps to reproduce
   - Environment details

---

**Built for reliable document processing with modern Python best practices.**
