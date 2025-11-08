# Landing AI Response Structure vs Current Database Schema
## Comprehensive Analysis & Improvement Plan

---

## 🔍 ULTRATHINK ANALYSIS

### Current State: What We're Losing

**Landing AI Provides:**
```json
{
  "markdown": "Full document text",
  "chunks": [
    {
      "id": "chunk-abc-123",
      "type": "text|table|figure|form|keyValue|attestation|...",
      "markdown": "Chunk content",
      "grounding": {
        "box": {"left": 100, "top": 200, "right": 500, "bottom": 300},
        "page": 5
      }
    }
  ],
  "splits": [
    {
      "class": "section",
      "identifier": "Item_1C_Cybersecurity",
      "pages": [5, 6, 7],
      "markdown": "Section content",
      "chunks": ["chunk-id-1", "chunk-id-2"]
    }
  ],
  "grounding": {...},
  "metadata": {
    "page_count": 12,
    "duration_ms": 3420,
    "credit_usage": 5,
    "job_id": "ade-job-xyz"
  }
}
```

**Current Storage (What We Store):**
```sql
documents.extracted_text = "Full markdown text"  -- Just a flat string!
documents.extraction_metadata = {
  "num_pages": 12,
  "num_chunks": 47,  -- Just a count, no actual chunks!
  "chunk_types": {"text": 35, "table": 8},  -- Counts only!
  "tables_found": 8  -- How many, but not WHICH or WHERE!
}
```

**What We're Throwing Away:**
1. ❌ **Individual chunk data** - Can't query specific chunks
2. ❌ **Spatial information** - Don't know WHERE on page
3. ❌ **Chunk types** - Can't differentiate text from tables
4. ❌ **Grounding boxes** - Can't highlight evidence
5. ❌ **Splits/sections** - Can't navigate document structure
6. ❌ **Chunk IDs** - Can't reference specific elements
7. ❌ **Page associations** - Can't say "violation on page 5"

### Critical Use Cases We NEED

#### 1. **Compliance Violation Evidence**
```
"Found material omission: CISO report mentions '47,000 records
exfiltrated' in TABLE on page 3, but Form 8-K only says
'hypothetical cyber risks' in TEXT on page 1"
```

**Requirements:**
- Link to specific chunk IDs
- Show exact page numbers
- Highlight bounding boxes
- Differentiate chunk types (table vs text)
- Display side-by-side evidence

#### 2. **Table-Specific Queries**
```
"Extract all incident statistics tables from CISO reports for Q4"
"Compare risk assessment tables between CISO and 8-K"
```

**Requirements:**
- Query chunks by type (type='table')
- Get table content separately
- Preserve table structure
- Link tables to violations

#### 3. **Section Analysis**
```
"Show all discrepancies in 'Item 1C - Cybersecurity' sections"
"Find inconsistencies in 'Risk Factors' across documents"
```

**Requirements:**
- Store splits data
- Query by section identifier
- Navigate document structure
- Compare equivalent sections

#### 4. **Spatial Evidence**
```
"Show me the exact location where this violation was found"
"Highlight the discrepancy on the PDF viewer"
```

**Requirements:**
- Store bounding box coordinates
- Know exact page numbers
- Enable PDF highlighting
- Support visual diff

---

## 📊 PROPOSED HYBRID ARCHITECTURE

### Strategy: **Selective Normalization with Denormalized Caching**

**Philosophy:**
1. Keep denormalized benefits for document-level operations
2. Add normalized tables for chunk-level operations
3. Cache frequently accessed data in JSONB
4. Use indexes strategically

### New Schema Design

#### **Option A: Fully Hybrid (RECOMMENDED)**

```sql
-- EXISTING (Enhanced)
documents {
  id UUID PK
  file_name VARCHAR(255)
  file_path TEXT
  file_hash VARCHAR(64) UNIQUE
  extracted_text TEXT  -- Full markdown (keep for full-text search)
  extraction_status VARCHAR(20)

  -- Enhanced JSONB
  extraction_data JSONB {
    "full_markdown": "...",
    "metadata": {
      "page_count": 12,
      "job_id": "ade-xyz",
      "duration_ms": 3420,
      "credit_usage": 5
    },
    "statistics": {
      "total_chunks": 47,
      "chunk_types": {"text": 35, "table": 8, "figure": 4},
      "total_tables": 8,
      "total_figures": 4
    },
    "splits_summary": [
      {"class": "section", "identifier": "Item_1C", "pages": [5, 6, 7]}
    ]
  }
}

-- NEW: Chunk-level data
document_chunks {
  id UUID PK
  document_id UUID FK -> documents.id (ON DELETE CASCADE)

  chunk_id VARCHAR(100) NOT NULL UNIQUE  -- Landing AI chunk ID
  chunk_type VARCHAR(50) NOT NULL INDEX  -- text, table, figure, form, etc.
  chunk_order INT NOT NULL  -- Original order in document

  content TEXT NOT NULL  -- Markdown content of this chunk

  -- Spatial data
  page_number INT NOT NULL INDEX
  bounding_box JSONB NOT NULL {
    "left": 100,
    "top": 200,
    "right": 500,
    "bottom": 300
  }

  -- Parent section (if in a split)
  split_identifier VARCHAR(100) INDEX  -- Links to splits

  created_at TIMESTAMP

  -- Indexes
  INDEX idx_chunks_document_type (document_id, chunk_type)
  INDEX idx_chunks_page (document_id, page_number)
  INDEX idx_chunks_split (document_id, split_identifier)
  GIN INDEX idx_chunks_bbox (bounding_box)
}

-- NEW: Document splits/sections
document_splits {
  id UUID PK
  document_id UUID FK -> documents.id (ON DELETE CASCADE)

  class VARCHAR(50) NOT NULL  -- section, chapter, etc.
  identifier VARCHAR(100) NOT NULL  -- Item_1C, Risk_Factors, etc.
  pages INT[] NOT NULL  -- [5, 6, 7]

  markdown TEXT  -- Combined content of this split
  chunk_ids TEXT[]  -- Array of chunk IDs in this split

  split_order INT NOT NULL
  created_at TIMESTAMP

  INDEX idx_splits_identifier (document_id, identifier)
  INDEX idx_splits_pages (document_id, pages) USING GIN
}

-- ENHANCED: Violations with chunk references
violations {
  id UUID PK
  source_document_id UUID FK
  target_document_id UUID FK

  -- Enhanced evidence with chunk references
  evidence JSONB {
    "source": {
      "quote": "47,000 records exfiltrated...",
      "chunk_id": "chunk-abc-123",  -- NEW: Direct chunk reference
      "chunk_type": "table",  -- NEW: What type of content
      "page": 3,
      "bounding_box": {...},  -- NEW: Exact location
      "section": "Impact Assessment",
      "context": "..."
    },
    "target": {
      "quote": "hypothetical cyber risks...",
      "chunk_id": "chunk-xyz-789",
      "chunk_type": "text",
      "page": 1,
      "bounding_box": {...},
      "section": "Item 1.05",
      "context": "..."
    },
    "discrepancy_type": "material_omission"
  }
}
```

#### **Option B: Pure Denormalized (Alternative)**

```sql
-- Everything in JSONB
documents {
  id UUID PK
  file_name VARCHAR(255)
  extracted_text TEXT

  -- Store EVERYTHING from Landing AI
  extraction_data JSONB {
    "full_markdown": "...",
    "chunks": [  -- Full chunks array
      {
        "id": "chunk-abc-123",
        "type": "table",
        "markdown": "...",
        "grounding": {"box": {...}, "page": 3}
      }
    ],
    "splits": [...],  -- Full splits array
    "metadata": {...}
  }
}

-- Query chunks using JSONB operators
SELECT
  id,
  file_name,
  jsonb_array_elements(extraction_data->'chunks') AS chunk
FROM documents
WHERE (jsonb_array_elements(extraction_data->'chunks')->>'type')::text = 'table';
```

---

## 🎯 RECOMMENDATION: **Option A (Hybrid)**

### Why Hybrid Wins

**✅ Advantages:**
1. **Fast chunk queries**: No JSONB unnesting needed
2. **Spatial indexes**: GIN indexes on bounding_box
3. **Type filtering**: Direct index on chunk_type
4. **Page navigation**: Simple WHERE clause
5. **Chunk references**: violations can FK to chunks
6. **Denorm benefits**: Document-level ops still fast
7. **Storage efficient**: Only store chunks once

**✅ Query Performance:**
```sql
-- Find all tables in document (FAST)
SELECT content, page_number, bounding_box
FROM document_chunks
WHERE document_id = $1 AND chunk_type = 'table'
ORDER BY chunk_order;

-- Find evidence location (FAST)
SELECT c.page_number, c.bounding_box, c.content
FROM document_chunks c
WHERE c.chunk_id = 'chunk-abc-123';

-- Compare sections (FAST)
SELECT s1.markdown, s2.markdown
FROM document_splits s1
JOIN document_splits s2 ON s1.identifier = s2.identifier
WHERE s1.document_id = $doc1 AND s2.document_id = $doc2;
```

**❌ Disadvantages:**
- Slightly more complex schema
- Need migration to add new tables
- JOIN needed for chunk + document

---

## 📋 IMPLEMENTATION PLAN

### Phase 1: Schema Enhancement (Week 1)

**1.1 Create New Tables**
```bash
alembic revision -m "add_document_chunks_and_splits_tables"
```

**1.2 Migration**
- Create `document_chunks` table
- Create `document_splits` table
- Add GIN indexes
- Backfill existing documents (if any)

**1.3 Update Models**
- `models/document_chunk.py`
- `models/document_split.py`
- Update `Document` model with relationships

### Phase 2: Landing AI Integration (Week 1-2)

**2.1 Update Landing AI Service**
```python
# services/landing_ai.py
async def parse_and_store_chunks(
    document_id: UUID,
    file_content: bytes,
    filename: str
) -> tuple[str, dict, list[DocumentChunk], list[DocumentSplit]]:
    """Parse document and prepare chunks/splits for storage."""
    response = await parse_document(file_content, filename)

    # Create chunk objects
    chunks = []
    for i, chunk_data in enumerate(response.chunks):
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_id=chunk_data.id,
            chunk_type=chunk_data.type,
            chunk_order=i,
            content=chunk_data.markdown,
            page_number=chunk_data.grounding.page,
            bounding_box=chunk_data.grounding.box
        )
        chunks.append(chunk)

    # Create split objects
    splits = []
    for i, split_data in enumerate(response.splits or []):
        split = DocumentSplit(
            document_id=document_id,
            class_=split_data.class_,
            identifier=split_data.identifier,
            pages=split_data.pages,
            markdown=split_data.markdown,
            chunk_ids=split_data.chunks,
            split_order=i
        )
        splits.append(split)

    return (
        response.markdown,
        build_extraction_data(response),
        chunks,
        splits
    )
```

**2.2 Update CRUD Operations**
```python
# crud/document.py
async def create_document(
    db: AsyncSession,
    upload_file: UploadFile,
    ...
) -> Document:
    # Upload to S3
    s3_key, file_hash, file_size, mime_type = await upload_file_to_s3(...)

    # Create document first (to get ID)
    document = Document(id=uuid4(), ...)
    db.add(document)
    await db.flush()  # Get ID without committing

    # Parse with Landing AI and create chunks
    text, metadata, chunks, splits = await parse_and_store_chunks(
        document.id, file_content, filename
    )

    # Store chunks and splits
    for chunk in chunks:
        db.add(chunk)
    for split in splits:
        db.add(split)

    # Update document
    document.extracted_text = text
    document.extraction_data = metadata
    document.extraction_status = "completed"

    await db.commit()
    return document
```

### Phase 3: API Enhancements (Week 2)

**3.1 New Endpoints**
```python
# GET /api/v1/documents/{id}/chunks
# - Filter by type, page
# - Return chunks with grounding

# GET /api/v1/documents/{id}/chunks/{chunk_id}
# - Get specific chunk details

# GET /api/v1/documents/{id}/tables
# - Get all tables

# GET /api/v1/documents/{id}/splits
# - Get document sections

# GET /api/v1/documents/{id}/page/{page_num}/chunks
# - Get all chunks on a specific page
```

**3.2 Enhanced Schemas**
```python
# schemas/chunk.py
class ChunkResponse(BaseModel):
    id: UUID
    chunk_id: str
    chunk_type: str
    page_number: int
    content: str
    bounding_box: dict
    split_identifier: Optional[str]

# schemas/violation.py
class ViolationEvidenceEnhanced(BaseModel):
    quote: str
    chunk_id: str  # NEW
    chunk_type: str  # NEW
    page: int
    bounding_box: dict  # NEW
    section: Optional[str]
```

### Phase 4: Violation Detection Integration (Week 3)

**4.1 AWS Bedrock Integration**
- Use chunks for targeted analysis
- Pass specific sections to Claude
- Link violations to chunk IDs

**4.2 Enhanced Evidence**
```python
async def detect_violations(
    source_doc: Document,
    target_doc: Document
) -> list[Violation]:
    # Get relevant chunks
    source_chunks = await get_chunks_by_type(source_doc.id, ["text", "table"])
    target_chunks = await get_chunks_by_type(target_doc.id, ["text", "table"])

    # Send to AWS Bedrock Claude
    violations = await bedrock_analyze_compliance(
        source_chunks, target_chunks
    )

    # Store with chunk references
    for violation in violations:
        violation.evidence = {
            "source": {
                "chunk_id": source_chunk.chunk_id,
                "chunk_type": source_chunk.chunk_type,
                "bounding_box": source_chunk.bounding_box,
                ...
            },
            "target": {...}
        }
```

### Phase 5: UI/Frontend Features (Week 4)

**5.1 PDF Viewer with Highlighting**
- Use bounding_box coordinates
- Highlight evidence on PDF
- Click violation → jump to page + highlight

**5.2 Side-by-Side Comparison**
- Show source and target chunks
- Visual diff with highlights
- Section-level navigation

---

## 🔢 STORAGE IMPACT ANALYSIS

### Current Storage (Per Document)

```
Document row: ~5KB
- extracted_text: 50KB (full text)
- extraction_metadata: 500B (summary)
Total: ~55KB per document
```

### Proposed Storage (Per Document)

```
Document row: ~10KB
- extracted_text: 50KB
- extraction_data: 2KB (enhanced metadata + summaries)

Chunks (assume 50 chunks avg):
- 50 rows × 1KB = 50KB

Splits (assume 10 splits avg):
- 10 rows × 500B = 5KB

Total: ~117KB per document
```

**Storage Increase:** ~2.1x

**Trade-off Analysis:**
- ✅ 2x storage → 10x query performance
- ✅ Enable critical compliance features
- ✅ Support spatial evidence
- ✅ Enable section comparisons
- ✅ Storage is cheap vs developer time

**For 10,000 documents:**
- Current: ~550MB
- Proposed: ~1.17GB
- Difference: ~620MB (negligible)

---

## 🚀 DECISION MATRIX

| Criteria | Current | Option A (Hybrid) | Option B (Pure JSONB) |
|----------|---------|-------------------|----------------------|
| Chunk queries | ❌ Can't | ✅ Fast | ⚠️ Slow (unnesting) |
| Spatial search | ❌ No | ✅ GIN indexes | ⚠️ Complex queries |
| Type filtering | ❌ No | ✅ Indexed | ⚠️ JSONB operators |
| Document queries | ✅ Fast | ✅ Fast | ✅ Fast |
| Storage size | ✅ Small | ⚠️ ~2x | ✅ ~1.5x |
| Complexity | ✅ Simple | ⚠️ More tables | ✅ Simple |
| Violation linking | ❌ No | ✅ FK to chunks | ⚠️ String IDs |
| Future proof | ❌ Limited | ✅ Extensible | ⚠️ Limited |

**Winner:** **Option A (Hybrid)** ✅

---

## ✅ FINAL RECOMMENDATION

### Implement Hybrid Architecture (Option A)

**Immediate Actions:**
1. ✅ Create migration for new tables
2. ✅ Update models with chunk/split relationships
3. ✅ Enhance Landing AI service to store chunks
4. ✅ Add chunk-specific API endpoints
5. ✅ Update violation evidence with chunk references

**Timeline:**
- Week 1: Schema + Migration
- Week 2: API enhancements + Testing
- Week 3: Violation integration
- Week 4: Frontend features

**Risk Mitigation:**
- ✅ Backward compatible (existing docs still work)
- ✅ Can migrate gradually (process on upload)
- ✅ No breaking API changes needed
- ✅ Storage increase is minimal

This architecture provides the foundation for:
- 🎯 Precise violation evidence
- 📊 Table extraction and comparison
- 📍 Spatial PDF highlighting
- 📑 Section-level analysis
- 🔍 Advanced compliance detection

**Ready to implement!** 🚀
