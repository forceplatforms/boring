# 🚀 ComplianceGuard AI - API Quick Start

## Quick Run (Without Docker)

### Option 1: Using Python directly

```bash
# Install dependencies with UV
uv pip install -e ".[dev]"

# Run the API server
python run_api.py
```

### Option 2: Using Make

```bash
# Start development server
make dev
```

### Option 3: Using uvicorn directly

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run with uvicorn
uvicorn complianceguard.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 Access the API Documentation

Once the server is running, open your browser:

- **Swagger UI (Interactive)**: http://localhost:8000/docs
- **ReDoc (Readable)**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🧪 Test the API with Mock Data

All endpoints return realistic mock data - no database or external services required!

### 1. Upload a Document

**Using Swagger UI:**
1. Go to http://localhost:8000/docs
2. Expand `POST /api/v1/documents/upload`
3. Click "Try it out"
4. Upload a file (any PDF or DOCX)
5. Set `doc_type` to `ciso_report`
6. Click "Execute"

**Using curl:**
```bash
# Create a dummy file
echo "Test CISO Report" > test_report.pdf

# Upload it
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@test_report.pdf" \
  -F "doc_type=ciso_report" \
  -F "doc_category=Incident_Report"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "test_report.pdf",
  "doc_type": "ciso_report",
  "doc_category": "Incident_Report",
  "file_size_bytes": 2457600,
  "extraction_status": "completed",
  "uploaded_by": "analyst@company.com",
  "created_at": "2025-11-07T14:32:00Z",
  "updated_at": "2025-11-07T14:32:00Z"
}
```

### 2. List All Documents

**Using curl:**
```bash
curl http://localhost:8000/api/v1/documents
```

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "file_name": "CISO_Report_October_2024.pdf",
      "doc_type": "ciso_report",
      "extraction_status": "completed",
      ...
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0,
  "has_more": false
}
```

### 3. Trigger a Compliance Scan

**Using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/scans/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "framework": "SEC_CYBER",
    "scan_type": "initial"
  }'
```

**Response:**
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440002",
  "framework": "SEC_CYBER",
  "scan_type": "initial",
  "status": "pending",
  "document_count": 12,
  "estimated_duration_seconds": 180,
  "created_at": "2025-11-07T17:00:00Z"
}
```

### 4. Check Scan Status

**Using curl:**
```bash
# Replace {scan_id} with the ID from previous response
curl http://localhost:8000/api/v1/scans/{scan_id}/status
```

**Response (simulates progress over time):**
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440002",
  "status": "running",
  "document_count": 12,
  "documents_processed": 7,
  "violations_found": 3,
  ...
}
```

### 5. View Violations

**Using curl:**
```bash
# List all violations
curl http://localhost:8000/api/v1/violations

# Get specific violation
curl http://localhost:8000/api/v1/violations/{violation_id}
```

**Response:**
```json
{
  "id": "650e8400-e29b-41d4-a716-446655440001",
  "severity": "critical",
  "status": "open",
  "violation_type": "material_omission",
  "finding_summary": "Material cybersecurity incident not disclosed in SEC filing",
  "rule_citation": "SEC Regulation S-K Item 1C",
  "confidence_score": 0.95,
  "evidence": {
    "source_quote": "Ransomware attack confirmed. 47,000 records exfiltrated...",
    "target_quote": "We may be subject to hypothetical cyber risks..."
  },
  "recommendations": [
    {
      "priority": "immediate",
      "description": "Alert General Counsel",
      "timeline": "Within 2 hours"
    }
  ]
}
```

### 6. Update Violation Status

**Using curl:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/violations/{violation_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "assigned",
    "assigned_to_email": "compliance@company.com",
    "assigned_to_name": "Jane Smith"
  }'
```

## 📊 Statistics Endpoints

Get aggregated statistics:

```bash
# Document statistics
curl http://localhost:8000/api/v1/documents/stats/summary

# Scan statistics
curl http://localhost:8000/api/v1/scans/stats/summary

# Violation statistics
curl http://localhost:8000/api/v1/violations/stats/summary
```

## 🏥 Health Checks

```bash
# Overall health
curl http://localhost:8000/health

# Readiness probe
curl http://localhost:8000/health/ready

# Liveness probe
curl http://localhost:8000/health/live
```

## 🎯 API Features

### Pagination

All list endpoints support pagination:

```bash
# Get first 10 items
curl "http://localhost:8000/api/v1/documents?limit=10&offset=0"

# Get next 10 items
curl "http://localhost:8000/api/v1/documents?limit=10&offset=10"
```

### Filtering

Filter results by various criteria:

```bash
# Filter documents by type
curl "http://localhost:8000/api/v1/documents?doc_type=ciso_report"

# Filter violations by severity
curl "http://localhost:8000/api/v1/violations?severity=critical&status=open"

# Filter scans by framework
curl "http://localhost:8000/api/v1/scans?framework=SEC_CYBER&status=completed"
```

### Search

Search in file names:

```bash
curl "http://localhost:8000/api/v1/documents?search=October"
```

## 🔑 API Response Format

All responses follow a consistent structure:

### Success Response (Single Item)
```json
{
  "id": "uuid",
  "field1": "value1",
  "created_at": "ISO8601 timestamp",
  "updated_at": "ISO8601 timestamp"
}
```

### Success Response (List)
```json
{
  "items": [...],
  "total": 100,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

### Error Response
```json
{
  "success": false,
  "error": "error_type",
  "message": "Human-readable error message",
  "details": {...}
}
```

## 🧩 Mock Data Behavior

The API includes realistic mock data:

- **Documents**: Pre-loaded with 3 sample documents (CISO reports and SEC filings)
- **Violations**: 5 pre-loaded violations with varying severities
- **Scans**: Simulates scan progress over time:
  - First 10 seconds: `pending`
  - 10-30 seconds: `running` with incremental progress
  - After 30 seconds: `completed` with full results

**Note:** Mock data is stored in memory and resets when you restart the server.

## 🎨 Swagger UI Tips

1. **Try It Out**: Click "Try it out" on any endpoint to make real requests
2. **Schema**: Click on schema names to see full model definitions
3. **Examples**: Each endpoint includes example requests/responses
4. **Authorize**: Future versions will have authentication (currently open)

## 🛠️ Development Tips

### Watch for changes
The server auto-reloads when you modify code:

```bash
python run_api.py  # Includes --reload by default
```

### View logs
All requests are logged with timestamps:

```
INFO:     127.0.0.1:54321 - "GET /api/v1/violations HTTP/1.1" 200 OK
```

### Test with Python
```python
import httpx

# List documents
response = httpx.get("http://localhost:8000/api/v1/documents")
print(response.json())

# Upload document
files = {"file": open("test.pdf", "rb")}
data = {"doc_type": "ciso_report"}
response = httpx.post(
    "http://localhost:8000/api/v1/documents/upload",
    files=files,
    data=data
)
print(response.json())
```

## 🚀 Next Steps

1. **Explore Swagger UI**: http://localhost:8000/docs
2. **Test all endpoints**: Try creating documents, triggering scans, viewing violations
3. **Review response models**: Check out the detailed schemas in Swagger
4. **Read the code**: All endpoints are in `src/complianceguard/api/v1/`

## 📝 API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| **Documents** | | |
| POST | `/api/v1/documents/upload` | Upload document |
| GET | `/api/v1/documents` | List documents |
| GET | `/api/v1/documents/{id}` | Get document details |
| PATCH | `/api/v1/documents/{id}` | Update document |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| GET | `/api/v1/documents/stats/summary` | Get statistics |
| **Scans** | | |
| POST | `/api/v1/scans/trigger` | Trigger scan |
| GET | `/api/v1/scans/{id}/status` | Check scan status |
| GET | `/api/v1/scans/{id}/results` | Get scan results |
| GET | `/api/v1/scans` | List scans |
| POST | `/api/v1/scans/{id}/cancel` | Cancel scan |
| GET | `/api/v1/scans/stats/summary` | Get statistics |
| **Violations** | | |
| GET | `/api/v1/violations` | List violations |
| GET | `/api/v1/violations/{id}` | Get violation details |
| PATCH | `/api/v1/violations/{id}` | Update violation |
| POST | `/api/v1/violations/{id}/acknowledge` | Acknowledge violation |
| GET | `/api/v1/violations/stats/summary` | Get statistics |
| **Health** | | |
| GET | `/health` | Overall health check |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/live` | Liveness probe |

---

**Enjoy exploring the ComplianceGuard AI API!** 🎉
