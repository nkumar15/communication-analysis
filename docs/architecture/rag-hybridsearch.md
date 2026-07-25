# Hybrid Search Tutorial: PostgreSQL Full-Text Search + Vector Search

**Last Updated:** December 24, 2025  
**Status:** Educational Guide

---

## Table of Contents

1. [Introduction to Hybrid Search](#introduction-to-hybrid-search)
2. [PostgreSQL Full-Text Search (BM25)](#postgresql-full-text-search-bm25)
3. [Vector Similarity Search](#vector-similarity-search)
4. [Reciprocal Rank Fusion (RRF)](#reciprocal-rank-fusion-rrf)
5. [Implementation in This Codebase](#implementation-in-this-codebase)
6. [LlamaIndex Integration](#llamaindex-integration)
7. [Alternative Architecture: Elasticsearch + PostgreSQL](#alternative-elasticsearch--postgresql-architecture)
8. [Performance Considerations](#performance-considerations)
9. [Best Practices](#best-practices)
10. [References](#references)

---

## Introduction to Hybrid Search

### What is Hybrid Search?

**Hybrid search combines multiple search techniques to improve retrieval accuracy.** The most common combination is:

1. **Keyword Search (BM25):** Finds exact/partial keyword matches
2. **Vector Search (Vectors):** Finds conceptually similar content

### Why Use Hybrid Search?

**Vector search alone has limitations:**
- ❌ May miss exact keyword matches (e.g., product names, technical terms)
- ❌ Can be affected by "semantic drift" *conceptually similar but contextually wrong*

**Keyword search alone has limitations:**
- ❌ Misses semantic similarity (synonyms, paraphrases)
- ❌ Requires exact word matching

**Hybrid search gets the best of both:**
- ✅ Finds exact keyword matches (BM25)
- ✅ Finds semantically similar content (vectors)
- ✅ Combines results intelligently using Reciprocal Rank Fusion

### Example Scenario

**Query:** "How do I reset my password?"

**BM25 Results (keyword-focused):**
1. "To reset your password, click 'Forgot Password'"
2. "Password reset links expire in 24 hours"

**Vector Results (semantic-focused):**
1. "Account recovery options include email verification"
2. "Change your login credentials from settings"

**Hybrid Results (combined):**
1. "To reset your password, click 'Forgot Password'" (in both)
2. "Password reset links expire in 24 hours" (BM25 + context)
3. "Account recovery options include email verification" (semantic match)

---

## PostgreSQL Full-Text Search (BM25)

### What is Full-Text Search?

PostgreSQL's full-text search provides keyword-based ranking similar to search engines. It's based on the **BM25 algorithm** (Best Matching 25), a probabilistic ranking function.

### Key Concepts

#### 1. tsvector - The Searchable Document

A `tsvector` is a preprocessed representation of text optimized for searching:

```sql
-- Convert text to tsvector
SELECT to_tsvector('english', 'The quick brown fox jumps over the lazy dog');

-- Result: 'brown':3 'dog':9 'fox':4 'jump':5 'lazi':8 'quick':2
```

**What happened?**
- Stop words removed (`the`, `over`)
- Words stemmed (`jumps` → `jump`, `lazy` → `lazi`)
- Positions tracked (`:3`, `:4` indicate word positions)

#### 2. tsquery - The Search Query

A `tsquery` represents the search query:

```sql
-- Simple query
SELECT to_tsquery('english', 'fox & dog');  -- Both words
SELECT to_tsquery('english', 'fox | dog');  -- Either word

-- Check if a document matches a query:
SELECT to_tsvector('english', 'The quick brown fox') @@ to_tsquery('english', 'fox');
-- Result: true
```

#### 3. ts_rank() and ts_rank_cd() – Ranking

Rank documents by relevance:

```sql
SELECT
    content,
    ts_rank_cd(to_tsvector('english', content), query) as rank
FROM documents,
    websearch_to_tsquery('english', 'quick fox') query
WHERE to_tsvector('english', content) @@ query
ORDER BY rank DESC;
```

**Ranking factors:**
- ✅ **Term frequency (TF):** How often the term appears
- ✅ **Inverse document frequency (IDF):** How rare the term is
- ✅ **Document length normalization**
- ✅ **Term proximity (for `ts_rank_cd`)**

### BM25 Algorithm Explained

**BM25 Score Formula:**

```
score(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))
```

**Where:**
- `D` = document
- `Q` = query
- `qi` = query term
- `f(qi, D)` = term frequency in document
- `|D|` = document length
- `avgdl` = average document length
- `k1, b` = tuning parameters (typically k1=1.2, b=0.75)
- `IDF(qi)` = inverse document frequency of term

**In plain English:**
- ✅ More frequent terms in document → higher score
- ✅ Rarer terms across ALL documents → higher score (normalization)
- ✅ Longer documents → score adjusted downward (normalization)

---

## Vector Similarity Search

### What is Vector Search?

Vector search finds documents that are semantically similar to a query, even if they don't share exact keywords.

### Key Concepts

#### 1. Embeddings

*Embeddings are numerical representations of text in high-dimensional space.*

```python
# Azure OpenAI text-embedding-3-large produces 3072-dimensional vectors
query = "How do I reset my password?"
embedding = [0.123, -0.456, 0.789, ..., 0.234]  # 3072 numbers
```

**Properties:**
- Similar meanings → similar vectors
- Can be compared using distance metrics
- Capture semantic relationships

#### 2. Distance Metrics

**Cosine Similarity (used in this codebase):**

```
similarity = cos(θ) = (A · B) / (||A|| × ||B||)
```

- **Range:** -1 (opposite) to 1 (identical)
- **Measures:** angle between vectors
- **Insensitive to magnitude**

**In PostgreSQL with pgvector:**

```sql
-- <=> operator calculates cosine distance (1 - cosine similarity)
SELECT 1 - (c.embedding <=> '[0.1, 0.2, 0.3]'::vector) as similarity
FROM chunks;

-- To get similarity score:
SELECT 1 - (c.embedding <=> '{embedding_str}'::vector) as similarity;
```

#### 3. pgvector Extension

**pgvector adds vector data types and operations to PostgreSQL:**

```sql
-- Create vector column
ALTER TABLE chunks ADD COLUMN embedding vector(3072);

-- Create ivfflat index for approximate nearest neighbor
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops);

-- Search
SELECT * FROM chunks ORDER BY embedding <=> query_embedding LIMIT 10;
```

---

## Reciprocal Rank Fusion (RRF)

### What is RRF?

**Reciprocal Rank Fusion is an algorithm that combines rankings from multiple search systems without needing to normalize scores.**

### Why RRF?

**The Problem:** Different search systems produce incompatible scores:

- **Vector search:** similarity scores (0.0 to 1.0)
- **BM25:** rank scores (unbounded, higher is better)

**Naive approaches fail:**

- ❌ **Simple averaging:** `(vector_score + bm25_score) / 2` — scales don't match!
- ❌ **Weighted average:** Requires manual tuning per dataset
- ❌ **Score normalization:** Loses information, sensitive to outliers

**RRF solution:** Use rank positions instead of raw scores!

### RRF Formula

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

**Where:**
- **d** = document
- **rank_i(d)** = rank of document d in search system i (1-based)
- **k** = constant (typically 60)

### Example Calculation

**Vector Search Results:**
1. Doc A (score 0.92)
2. Doc B (score 0.89)
3. Doc C (score 0.78)

**BM25 Search Results:**
1. Doc B (score 12.3)
2. Doc D (score 9.8)
3. Doc A (score 6.4)

**RRF Scores (k=60):**

**Doc A:**
- Vector rank: 1 → 1/(60+1) = 0.0164
- BM25 rank: 3 → 1/(60+3) = 0.0159
- **Total: 0.0323**

**Doc B:**
- Vector rank: 2 → 1/(60+2) = 0.0161
- BM25 rank: 1 → 1/(60+1) = 0.0164
- **Total: 0.0325 ← Highest!**

**Doc C:**
- Vector rank: 3 → 1/(60+3) = 0.0159
- BM25 rank: not present = 0
- **Total: 0.0159**

**Doc D:**
- Vector rank: not present = 0
- BM25 rank: 2 → 1/(60+2) = 0.0161
- **Total: 0.0161**

**Final Ranking: B, A, D, C**

### Key Points:

- ✅ Uses rank position (1, 2, 3, ...) not raw scores
- ✅ k=60 is a standard constant (reduces impact of top-ranked items)
- ✅ Documents in both result sets get scores from both
- ✅ Final ranking by combined RRF score

### Why k=60?

The constant **k=60** is chosen to:

- **Dampen top-ranked items:** Prevents single search method from dominating
- **Give each rank k still contributes meaningfully**
- **Empirically validated:** Works well across diverse datasets

**Effect of k:**
- **Small k (e.g., 10):** Top-ranked items have large advantage
- **Large k (e.g., 100):** Flatter distribution, less differentiation
- **k = 60:** Sweet spot for most use cases

---

## Implementation in This Codebase

### Complete Hybrid Search Flow

**User Query:** *"How do I reset my password?"*

1. **EMBED QUERY (RAGService)**
   - Azure OpenAI embedding API
   - Result: [0.123, -0.456, ..., 0.234] (3072 dims)

2. **HYBRID SEARCH (search_hybrid_chunks)**
   - **Vector search (search_similar_chunks)**
     - SQL: SELECT ... WHERE 1 - (embedding <=> query_embedding) >= 0.3
     - Top 10 results with cosine similarity scores
     - Example: [("Reset password guide", 0.85), ...]
   
   - **BM25 Search (search_bm25_chunks)**
     - SQL: SELECT ... WHERE content_tsv @@ websearch_to_tsquery('reset password')
     - Top 10 results with BM25 rank scores
     - Example: [("Password reset FAQ", 12.3), ...]
   
   - **RRF Fusion (reciprocal_rank_fusion)**
     - Combine rankings using RRF formula
     - Return top 5 fused results
     - Example: [("Reset password guide", 0.0325), ...]

3. **BUILD CONTEXT (RAGService._build_context_prompt)**
   - Format retrieved chunks into prompt
   - Add instructions for LLM

4. **GENERATE RESPONSE (RAGService._generate_response)**
   - Azure OpenAI API
   - Answer query: "To reset your password, click the 'Forgot Password' link..."

5. **LOG QUERY (RAGService._log_query)**
   - Store query, response, and metadata in database

### Step 1: Migration Setup

**File:** `007_add_fulltext_search.sql`

```sql
-- Add tsvector column to store preprocessed text
ALTER TABLE chunks ADD COLUMN content_tsv tsvector;

-- Create GIN index for fast searching
CREATE INDEX chunks_content_tsv_idx ON chunks USING GIN (content_tsv);

-- Update existing rows
UPDATE chunks SET content_tsv = to_tsvector('english', content);

-- Auto-update trigger (keeps tsvector in sync with content)
CREATE OR REPLACE FUNCTION chunks_content_tsv_trigger() RETURNS trigger AS $$
BEGIN
  NEW.content_tsv := to_tsvector('english', NEW.content);
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER chunks_content_tsv_update
  BEFORE INSERT OR UPDATE ON chunks
  FOR EACH ROW
  EXECUTE FUNCTION chunks_content_tsv_trigger();
```

**Key Points:**
- ✅ `content_tsv` column stores the preprocessed text
- ✅ GIN index enables fast searches (like an inverted index)
- ✅ Trigger automatically updates `content_tsv` when content changes
- ✅ `'english'` configuration handles stemming and stop words

### Step 2: Vector Search Function

**File:** `vector_utils.py`

```python
def search_similar_chunks(
    session: Session,
    query_embedding: List[float],
    tenant_id: str,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
) -> List[Tuple[Chunk, float]]:
    """Search for similar chunks using cosine similarity."""
    
    # Convert embedding to pgvector format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    query = text("""
        SELECT
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.chunk_metadata,
            c.created_at,
            1 - (c.embedding <=> '{embedding_str}'::vector) as similarity
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.tenant_id = :tenant_id
        AND 1 - (c.embedding <=> '{embedding_str}'::vector) >= :threshold
        ORDER BY c.embedding <=> '{embedding_str}'::vector
        LIMIT :top_k
    """)
    
    results = session.execute(
        query,
        {
            "tenant_id": tenant_id,
            "threshold": similarity_threshold,
            "top_k": top_k,
        }
    ).fetchall()
    
    # Convert to Chunk objects with scores
    chunks_with_scores = []
    for row in results:
        chunk = Chunk(...)
        chunks_with_scores.append((chunk, float(row.similarity)))
    
    return chunks_with_scores
```

**How it works:**
1. Convert query text to embeddings [3072 dimensions]
2. Calculate cosine distance: `embedding <=> query_embedding`
3. Filter by similarity threshold
4. Return top K results

### Step 3: BM25 Search Function

**File:** `vector_utils.py`

```python
def search_bm25_chunks(
    session: Session,
    query_text: str,
    tenant_id: str,
    top_k: int = 10,
) -> List[Tuple[Chunk, float]]:
    """Search for chunks using BM25 (PostgreSQL full-text search)."""
    
    query = text("""
        SELECT
            c.id,
            c.document_id,
            c.content,
            c.chunk_index,
            c.chunk_metadata,
            c.created_at,
            ts_rank_cd(c.content_tsv, query) as rank
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        CROSS JOIN websearch_to_tsquery('english', :query_text) query
        WHERE d.tenant_id = :tenant_id
        AND c.content_tsv @@ query
        ORDER BY rank DESC
        LIMIT :top_k
    """)
    
    results = session.execute(
        query,
        {"tenant_id": tenant_id, "query_text": query_text, "top_k": top_k}
    ).fetchall()
    
    return [(Chunk(...), float(row.rank)) for row in results]
```

**How it works:**
1. Convert query to tsquery using websearch (user-friendly)
2. Filter chunks where `content_tsv @@ query` (documents that match)
3. Rank by `ts_rank_cd()` (relevance score)
4. Return top K results

### Step 4: RRF Fusion Function

**File:** `vector_utils.py`

```python
def reciprocal_rank_fusion(
    vector_results: List[Tuple[Chunk, float]],
    bm25_results: List[Tuple[Chunk, float]],
    top_k: int = 5,
    k: int = 60,
) -> List[Tuple[Chunk, float]]:
    """Combine vector and BM25 results using Reciprocal Rank Fusion."""
    
    # Calculate RRF scores
    rrf_scores: Dict[str, float] = defaultdict(float)
    chunk_map: Dict[str, Chunk] = {}
    
    # Add vector results (rank starts at 1)
    for rank, (chunk, score) in enumerate(vector_results, start=1):
        chunk_id = str(chunk.id)
        rrf_scores[chunk_id] += 1.0 / (k + rank)
        chunk_map[chunk_id] = chunk
    
    # Add BM25 results (rank starts at 1)
    for rank, (chunk, score) in enumerate(bm25_results, start=1):
        chunk_id = str(chunk.id)
        rrf_scores[chunk_id] += 1.0 / (k + rank)
        chunk_map[chunk_id] = chunk
    
    # Sort by RRF score descending
    sorted_chunks = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:top_k]
    
    return [(chunk_map[chunk_id], score) for chunk_id, score in sorted_chunks]
```

### Step 5: Hybrid Search Orchestration

**File:** `vector_utils.py`

```python
def search_hybrid_chunks(
    session: Session,
    query_text: str,
    query_embedding: List[float],
    tenant_id: str,
    top_k: int = 5,
    vector_top_k: int = 10,
    bm25_top_k: int = 10,
    similarity_threshold: float = 0.5,
) -> List[Tuple[Chunk, float]]:
    """Execute hybrid search combining vector and BM25."""
    
    # Get vector results
    vector_results = search_similar_chunks(
        session=session,
        query_embedding=query_embedding,
        tenant_id=tenant_id,
        top_k=vector_top_k,
        similarity_threshold=similarity_threshold,
    )
    
    # Get BM25 results
    bm25_results = search_bm25_chunks(
        session=session,
        query_text=query_text,
        tenant_id=tenant_id,
        top_k=bm25_top_k,
    )
    
    # Combine with RRF
    return reciprocal_rank_fusion(
        vector_results=vector_results,
        bm25_results=bm25_results,
        top_k=top_k,
    )
```

### Step 6: RAG Service Entry Point

**File:** `rag_service.py`

```python
def query_documents(
    self,
    session: Session,
    tenant_id: UUID,
    query_text: str,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
) -> dict:
    """Execute RAG query pipeline."""
    
    # Step 1: Embed query
    query_embedding = self._embed_query(query_text)
    
    # Step 2: Hybrid search
    chunks_with_scores = search_hybrid_chunks(
        session=session,
        query_text=query_text,
        query_embedding=query_embedding,
        tenant_id=str(tenant_id),
        top_k=top_k or 5,
        similarity_threshold=similarity_threshold or 0.5,
    )
    
    # Step 3: Build context
    context_prompt = self._build_context_prompt(query_text, chunks_with_scores)
    
    # Step 4: Generate response
    response_text = self._generate_response(context_prompt)
    
    # Step 5: Log query
    query_record = self._log_query(
        session, tenant_id, query_text, response_text, execution_time, chunks_with_scores
    )
    
    return {
        "query_id": query_record.id,
        "response": response_text,
        "retrieved_chunks": chunks_data,
    }
```

---

## LlamaIndex Integration

### LlamaIndex Overview

**LlamaIndex is a framework for building RAG applications.** It provides high-level abstractions for:

- Document loading and parsing
- Chunking and embedding
- Vector stores and retrievers
- Query engines

### What We Use from LlamaIndex

**Document processing:**

```python
# Document processing (in document_service.py)
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

# Load documents
documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

# Chunk documents
splitter = SentenceSplitter(
    chunk_size=1024,
    chunk_overlap=20,
)
nodes = splitter.get_nodes_from_documents(documents)

# Embed nodes (using Azure OpenAI)
for node in nodes:
    embedding = embedding_client.embeddings.create(
        input=node.text,
        model="text-embedding-3-large"
    ).data[0].embedding
```

### What We DON'T Use from LlamaIndex

- ❌ **VectorStoreIndex** (we use raw SQL with pgvector)
- ❌ **Query engines** (we implement RAGService manually)
- ❌ **Built-in hybrid retrievers** (we implement RRF manually)

### Why Custom Implementation?

**Reasons we didn't use LlamaIndex's built-in hybrid search:**

1. **Tenant isolation:** Need custom SQL queries with `tenant_id` filtering
2. **pgvector integration:** Direct PostgreSQL integration for RLS policies
3. **Control:** Fine-grained control over BM25 + vector fusion
4. **Performance:** Optimized SQL queries vs abstraction overhead

### LlamaIndex Hybrid Search (Reference)

**If you wanted to use LlamaIndex's built-in hybrid search, it would look like:**

```python
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever, BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever

# Create vector retriever
vector_retriever = VectorIndexRetriever(index=vector_index)

# Create BM25 retriever
bm25_retriever = BM25Retriever.from_defaults(nodes=nodes)

# Combine with fusion
hybrid_retriever = QueryFusionRetriever(
    [vector_retriever, bm25_retriever],
    similarity_top_k=10,
    num_queries=1,  # No query generation
    mode="reciprocal_rerank",  # RRF
)
```

**Why we don't use it:**
- Doesn't support multi-tenancy out of the box
- Can't leverage PostgreSQL RLS
- Less control over SQL queries and optimization

---

## Alternative: Elasticsearch + PostgreSQL Architecture

### Key Design Decisions

- ✅ Elasticsearch handles both BM25 and vector search
- ✅ Elasticsearch does RRF fusion natively
- ✅ PostgreSQL used only for metadata and analytics

### Architecture Diagrams

#### Current: PostgreSQL-Only Architecture

```
┌─────────────────────────────┐
│    Application Layer        │
│  (FastAPI + WebService)     │
└──────────────┬──────────────┘
               │
               │ All operations
               ↓
┌──────────────────────────────┐
│     PostgreSQL + pgvector     │
│                              │
│  ┌────────────────────────┐ │
│  │  Operational Tables:   │ │
│  │  - tenants             │ │
│  │  - documents           │ │
│  │  - queries             │ │
│  └────────────────────────┘ │
│                              │
│  ┌────────────────────────┐ │
│  │  chunks Table:         │ │
│  │  - content (TEXT)      │ │
│  │  - content_tsv (tsvector) │ │
│  │  - embedding (vector(3072)) │ │
│  │  - GIN index (full-text) │ │
│  │  - IVFFlat index (vectors) │ │
│  └────────────────────────┘ │
└──────────────────────────────┘
```

#### Alternative: Elasticsearch + PostgreSQL Architecture

```
┌──────────────────────────────┐
│     Application Layer        │
│   (FastAPI + WebService)     │
└───────┬──────────┬───────────┘
        │          │
Metadata│          │Search queries
writes  │          │
        ↓          ↓
┌─────────┐   ┌──────────────┐
│PostgreSQL│   │Elasticsearch │
│          │   │              │
│Operational:│ │Chunks Index: │
│- tenants  │ │- content (text)│
│- documents│ │- embedding    │
│- queries  │ │  (dense_vector)│
│- metadata │ │- chunk_id (UUID)│
│          │   │- document_id  │
│No chunks │   │- tenant_id    │
│table!    │   │              │
│          │   │Inverted Index:│
└──────────┘   └──────────────┘
```

### Elasticsearch Hybrid Search Query

**POST /chunks/_search**

```json
{
  "query": {
    "hybrid": {
      "queries": [
        {
          "match": {
            "content": {
              "query": "reset password",
              "boost": 1.0
            }
          }
        },
        {
          "knn": {
            "field": "embedding",
            "query_vector": [0.123, -0.456, ..., 0.234],
            "k": 10,
            "num_candidates": 50,
            "boost": 1.0
          }
        }
      ]
    }
  },
  "rank": {
    "rrf": {
      "window_size": 50,
      "rank_constant": 60
    }
  },
  "size": 5,
  "filter": {
    "term": {
      "tenant_id": "12de9667-eb0b-12d3-a456-426614174000"
    }
  }
}
```

### Document Ingestion Flow

**User uploads document**

1. **SAVE METADATA (PostgreSQL)**
   - Insert into `documents` table
   - Store: filename, tenant_id, upload_date, status
   - Get document_id (UUID)

2. **PROCESS DOCUMENT (Application)**
   - Parse PDF/TXT
   - Chunk content (SentenceSplitter)
   - Generate embeddings (Azure OpenAI)

3. **INDEX IN ELASTICSEARCH**
   - Bulk index chunks
   - Store: content, embedding, chunk_id, document_id, tenant_id
   - Elasticsearch auto-builds indexes (inverted + kNN)

4. **UPDATE STATUS (PostgreSQL)**
   - Set document status = 'completed'

**Key Changes:**
- ✅ Metadata goes to PostgreSQL (source of truth)
- ✅ Search data goes to Elasticsearch (optimized for search)
- ✅ No duplication of content in PostgreSQL

### Query Flow

**User Query:** *"How do I reset my password?"*

1. **EMBED QUERY (Application)** - Azure OpenAI embedding API
2. **HYBRID SEARCH (Elasticsearch)** - Single API call performs BM25, kNN, and RRF fusion
3. **ENRICH WITH METADATA (PostgreSQL)** - Add document names to results
4. **GENERATE RESPONSE (Application)** - Azure OpenAI API

### Feature Comparison Matrix

| Feature | PostgreSQL-Only | Elasticsearch + PostgreSQL | Winner |
|---------|----------------|----------------------------|---------|
| **Search Performance** | 200-700ms | 50-150ms | 🏆 ES |
| **Setup Complexity** | Low (1 database) | High (2 systems) | 🏆 PG |
| **Operational Complexity** | Low | High | 🏆 PG |
| **Cost** | $50-200/month | $200-500/month | 🏆 PG |
| **Data Consistency** | Strong ACID | Eventual | 🏆 PG |
| **Tenant Isolation** | ✅ (database-level) | Application-level | 🏆 PG |
| **Advanced Search** | Basic full-text | Rich features | 🏆 ES |
| **Horizontal Scaling** | Limited | Excellent | 🏆 ES |
| **Vector Performance** | IVFFlat (good) | HNSW (better) | 🏆 ES |
| **Analytics on Search** | Requires custom SQL | Built-in aggregations | 🏆 ES |
| **Fuzzy/Synonym Search** | Limited | Native support | 🏆 ES |
| **Learning Curve** | Low (1 technology) | High (2 technologies) | 🏆 PG |

### Cost Analysis

**PostgreSQL-Only (managed service like AWS RDS):**
- db.r6g.xlarge (4 vCPU, 32GB RAM): $350/month
- Storage (500GB SSD): $115/month
- Backups (automated): $30/month
- **Total: ~$515/month**

**Elasticsearch + PostgreSQL (managed services):**
- PostgreSQL: db.r6g.large (2 vCPU, 16GB RAM): $175/month
- Elasticsearch 3-node cluster (AWS OpenSearch):
  - r6g.xlarge.search x 3 nodes: $500/month
  - Storage (500GB): $50/month
  - Snapshots: $25/month
- Message queue (RabbitMQ/SQS): $40/month
- **Total: ~$775/month (+50% cost increase)**

### Challenges

#### Challenge 1: Data Synchronization

**Problem:** What if Elasticsearch indexing fails after PostgreSQL commit?

**Solution:** Use message queue (RabbitMQ, Kafka) for reliable async processing:

```python
# Step 1: Save to PostgreSQL + publish event
session.add(document)
session.commit()
message_queue.publish("document.created", document_id)

# Step 2: Background worker indexes in Elasticsearch
@worker.task
def index_document(document_id):
    chunks = get_chunks(document_id)
    retry_with_backoff(lambda: es.bulk(index="chunks", body=chunks))
```

#### Challenge 2: Tenant Isolation

**Problem:** Easy to forget tenant filter

**Solution:** Create helper wrapper that always adds tenant filter:

```python
class TenantAwareElasticsearch:
    def search(self, index, query, tenant_id):
        tenant_query = {
            "bool": {
                "must": [query],
                "filter": [{"term": {"tenant_id": tenant_id}}]
            }
        }
        return self.es.search(index=index, query=tenant_query)
```

### Migration Path

**Phase 1: Dual Write (No Downtime)**

```python
def process_document(document):
    save_to_postgres(document)
    try:
        index_to_elasticsearch(document)
    except Exception as e:
        logger.warn(f"ES indexing failed: {e}")
```

**Phase 2: Backfill Historical Data**

```python
def backfill_elasticsearch():
    chunks = session.query(Chunk).all()
    for batch in batched(chunks, size=1000):
        es.bulk(index="chunks", body=batch)
```

**Phase 3: Gradual Traffic Shift**

```python
def search_chunks(query, tenant_id):
    if feature_flags.use_elasticsearch(tenant_id):
        return elasticsearch_search(query, tenant_id)
    else:
        return postgres_search(query, tenant_id)
```

**Phase 4: Remove PostgreSQL Chunks Table**

```sql
DROP TABLE chunks;
```

---

## Performance Considerations

### Indexing

**Vector Index (pgvector):**

```sql
-- IVFFlat index (approximate nearest neighbor)
CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Number of clusters
```

**Full-Text Index (PostgreSQL):**

```sql
-- GIN index (inverted index for fast keyword search)
CREATE INDEX chunks_content_tsv_idx ON chunks USING GIN (content_tsv);
```

### Typical Query Times

- **Vector search:** 100-300ms (depends on index size, lists parameter)
- **BM25 search:** 10-30ms (GIN index is very fast)
- **RRF fusion:** 1-5ms (in-memory processing)
- **Total:** < 1 second for most queries

### Optimization Tips

**1. Adjust IVFFlat index parameters**
- More lists = faster search, slightly lower recall
- Typical HNSW = `sqrt(num_rows)`

**2. Set similarity_threshold appropriately:**
- Too high (e.g., 0.9): Miss relevant results
- Too low (e.g., 0.3): Return irrelevant results
- Sweet spot: 0.5-0.7

**3. Tune vector_top_k and bm25_top_k:**
- Retrieve more candidates (e.g., 10-20) for fusion
- Return fewer final results (e.g., 5)

**4. Use connection pooling:**
- SQLAlchemy manages connections efficiently
- Configure pool size based on load

---

## Best Practices

### When to Use Hybrid Search

✅ **Use hybrid search when:**
- Users ask questions with specific keywords (product names, technical terms)
- You need both semantic understanding AND exact matching
- Your corpus has domain-specific terminology
- You want robust retrieval across query types

❌ **Skip hybrid search when:**
- Pure semantic search is sufficient
- Query latency is critical (<100ms required)
- You don't have full-text search infrastructure

### Configuration Guidelines

**Vector Search:**
- `top_k`: 5-10 results
- `similarity_threshold`: 0.5-0.7 (tune based on evaluation)
- `embedding_model`: Use same model for indexing and querying

**BM25 Search:**
- `top_k`: 10-20 results (BM25 is fast, so get more candidates)
- `language`: Match your corpus language (`'english'`, `'spanish'`, etc)

**RRF Fusion:**
- `k`: 60 (standard, rarely needs tuning)
- `top_k`: Final number of results (5-10)

### When to Use Each Approach

#### ✅ Use PostgreSQL-Only When:

1. Starting out / MVP: Don't prematurely optimize
2. Budget constrained
3. Small team (<5 engineers)
4. Simple search needs: Basic full-text search is sufficient
5. Strong consistency required: Can't tolerate eventual consistency

**Sweet spot:**
- 1-1000 tenants
- 100K-10M document chunks
- 10-100 queries per second
- $100K-$1M ARR companies

#### ✅ Use Elasticsearch + PostgreSQL When:

1. Scale requirements: >10M chunks, >100 searches/sec
2. Advanced search needed: Fuzzy, synonyms, complex queries
3. Performance critical: Sub-100ms search latency required

### Decision Framework

**Start with PostgreSQL-Only if:**
- ✅ Early stage MVP, validating product-market fit
- ✅ Budget constrained, <$10M ARR
- ✅ Small team (<5 engineers)
- ✅ Basic search requirements

**Migrate to Elasticsearch when you hit these signals:**
- 🚨 Search latency >1 second consistently
- 🚨 PostgreSQL CPU >70% on search queries
- 🚨 Need advanced features (fuzzy, synonyms, complex queries)
- 🚨 Search quality is competitive differentiator

**The sweet spot:** PostgreSQL-only for first 6-12 months, evaluate migration once you have scale and revenue.

### Monitoring

**Track these metrics:**
- Query latency (p50, p95, p99)
- Vector search recall (how many relevant docs retrieved)
- Fusion contribution (% of final results from BM25 vs vector)
- Cache hit rate (if caching embeddings)

### Testing

**Evaluation dataset:**
- Create golden test sets with known good results
- Measure precision@k and recall@k
- Compare hybrid vs vector-only vs BM25-only

---

## Summary

### Key Takeaways

**1. PostgreSQL Full-Text Search**
- Uses `tsvector` for preprocessed text
- BM25 ranking algorithm (term frequency + rarity + normalization)
- Fast with GIN indexes
- Good for exact keyword matching

**2. Vector Similarity Search**
- Uses embeddings (semantic representation)
- Cosine similarity for comparing vectors
- pgvector extension for PostgreSQL
- Good for conceptual similarity

**3. Reciprocal Rank Fusion**
- Combines rankings without normalizing scores
- Formula: `RRF_score = Σ 1/(k + rank)`
- Simple, effective, no tuning needed
- Best of both search methods

**4. Implementation in This Codebase**
- Custom hybrid search with full tenant isolation
- Direct SQL queries for performance
- RRF fusion for combining results
- Azure OpenAI for embeddings and LLM

**5. LlamaIndex**
- Used for document processing (chunking, embedding)
- NOT used for hybrid search (custom implementation)
- Provides high-level abstractions for RAG

**6. Elasticsearch Alternative**
- Better performance (50-150ms vs 200-700ms)
- Higher cost (~50% increase)
- More complexity (2 systems to manage)
- Better for scale (>10M chunks)

---

## References

### PostgreSQL Full-Text Search
- [PostgreSQL Full-Text Search Docs](https://www.postgresql.org/docs/current/textsearch.html)
- [BM25 Algorithm Explanation](https://en.wikipedia.org/wiki/Okapi_BM25)

### pgvector
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector Performance Tuning](https://github.com/pgvector/pgvector#performance)

### Reciprocal Rank Fusion
- [Original RRF Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [RRF Explained (Blog)](https://www.elastic.co/blog/improving-information-retrieval-elastic-stack-hybrid)

### LlamaIndex
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [LlamaIndex Retrievers](https://docs.llamaindex.ai/en/stable/module_guides/querying/retriever/)

### Codebase Files
- Migration: `services/b2c/migrations/007_add_fulltext_search.sql`
- Vector Utils: `services/b2c/app/utils/vector_utils.py`
- Search Service: `services/b2c/app/services/search_service.py`

---

## Next Steps

To learn more:

1. **Experiment:** Run queries, observe vector vs BM25 vs hybrid results
2. **Tune:** Adjust `similarity_threshold`, `top_k`, & parameters
3. **Evaluate:** Create test datasets, measure metrics
4. **Optimize:** Tune indexes, monitor query performance
