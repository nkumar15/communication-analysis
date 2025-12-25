# RAG (Retrieval-Augmented Generation) Specification

**Version:** 1.0  
**Last Updated:** December 24, 2025  
**Status:** Draft - Planning Phase  
**Architecture:** Elasticsearch + PostgreSQL

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Use Cases for SaaS Boilerplate](#use-cases-for-saas-boilerplate)
3. [Architecture Overview](#architecture-overview)
4. [Feature Roadmap](#feature-roadmap)
5. [Implementation Phases](#implementation-phases)
6. [Advanced Features Timeline](#advanced-features-timeline)
7. [Cost & Resource Planning](#cost--resource-planning)
8. [Success Metrics](#success-metrics)

---

## Executive Summary

This specification outlines the implementation of a Retrieval-Augmented Generation (RAG) system for our multi-tenant SaaS boilerplate using **Elasticsearch + PostgreSQL** architecture. The system will enable intelligent document search and question-answering capabilities across tenant-specific knowledge bases.

### Key Decisions

- **Architecture:** Elasticsearch + PostgreSQL (dual-system approach)
- **Search Strategy:** Hybrid search (BM25 + Vector + RRF fusion)
- **Task Queue:** Celery 5.x with Redis broker
- **Tenant Isolation:** Application-level filtering with strict tenant_id enforcement
- **LLM Provider:** Pluggable (Azure OpenAI, OpenAI, Anthropic, Ollama for local dev)
- **Embedding Model:** Pluggable (OpenAI, Cohere, sentence-transformers for local dev)
- **Document Processing:** LlamaIndex for chunking, parsing, and advanced routing
- **Object Storage:** Pluggable (S3, Azure Blob, MinIO for local dev)

### Strategic Rationale

While PostgreSQL-only would be simpler, we're choosing Elasticsearch + PostgreSQL because:

1. **Future-proofing:** Easier to scale horizontally as the product grows
2. **Performance:** Sub-100ms search latency enables real-time features
3. **Advanced features:** Opens doors to fuzzy search, synonyms, aggregations
4. **Competitive advantage:** Best-in-class search experience from day one

---

## Use Cases for SaaS Boilerplate

### Phase 1: Foundation (MVP)

#### 1.1 Knowledge Base Search
**Target Users:** All tenant users  
**Description:** Search through uploaded documentation, guides, and help articles

**User Story:**
> As a team member, I want to search our internal documentation so that I can quickly find answers without asking colleagues.

**Example Queries:**
- "How do I configure SSO?"
- "What's our refund policy?"
- "Steps to reset a user's password"

**Value Proposition:**
- Reduces support ticket volume
- Faster onboarding for new team members
- Self-service documentation access

**LlamaIndex Features:**
- **VectorStoreIndex:** Core retrieval mechanism
- **SimpleDirectoryReader:** Document loading
- **SentenceSplitter:** Smart chunking

---

#### 1.2 Q&A Assistant
**Target Users:** All tenant users  
**Description:** AI-powered assistant that answers questions based on tenant's knowledge base

**User Story:**
> As a user, I want to ask questions in natural language and get accurate answers from our documentation so that I don't have to read through multiple pages.

**Example Interaction:**
```
User: "How long does it take to process a refund?"
Assistant: "Based on your refund policy document, refunds are processed within 
5-7 business days. You'll receive a confirmation email once the refund is initiated."
```

**Value Proposition:**
- Instant answers 24/7
- Reduces dependency on human support
- Consistent, accurate responses

**LlamaIndex Features:**
- **QueryEngine:** End-to-end query processing
- **Response Synthesizer:** Answer generation from chunks
- **Prompt Templates:** Customizable system prompts

---

#### 1.3 Document Management
**Target Users:** Admins, Owners  
**Description:** Upload, organize, and manage documents that power the RAG system

**User Story:**
> As an admin, I want to upload and organize our company documentation so that our team can search and get AI-powered answers from it.

**Features:**
- Upload PDFs, DOCX, TXT files
- View document status (processing, indexed, failed)
- Delete/update documents
- View indexing metadata (chunk count, last updated)

**Value Proposition:**
- Easy content management
- Version control for documentation
- Audit trail for compliance

---

### Phase 2: Enhanced Features (3-6 months)

#### 2.1 Workspace-Specific Knowledge Bases
**Target Users:** B2C users with multiple workspaces  
**Description:** Each workspace has its own isolated knowledge base

**User Story:**
> As a user with multiple workspaces, I want each workspace to have its own knowledge base so that information doesn't leak between projects.

**Technical Implementation:**
- Extend tenant_id filtering to workspace_id
- Workspace-scoped document uploads
- Workspace switcher in RAG interface

**Value Proposition:**
- Better organization for multi-project teams
- Privacy and data isolation
- Flexibility for different use cases per workspace

**LlamaIndex Features:**
- **Index Namespacing:** Workspace-scoped indexes
- **Metadata Filtering:** Workspace-level access control

---

#### 2.2 Semantic Similarity Suggestions
**Target Users:** All users  
**Description:** While typing a question, suggest related questions and documents

**User Story:**
> As I type my question, I want to see similar questions that have been asked before so that I can find answers faster.

**Example:**
```
User types: "How to reset pass"
Suggestions:
- "How do I reset my password?" (asked 45 times)
- "Password reset link expired - what to do?"
- Related docs: "User Account Management Guide"
```

**Value Proposition:**
- Faster discovery
- Learn from common queries
- Reduce duplicate questions

**LlamaIndex Features:**
- **ElasticsearchRetriever:** Autocomplete queries
- **Query Transformation:** Query expansion and refinement

---

#### 2.3 Query Analytics Dashboard
**Target Users:** Admins, Owners  
**Description:** Insights into what users are searching for and document effectiveness

**Metrics Tracked:**
- Top queries (daily/weekly/monthly)
- Queries with no results (content gaps)
- Most referenced documents
- Average query latency
- User satisfaction ratings

**Value Proposition:**
- Identify documentation gaps
- Prioritize content creation
- Monitor system performance
- Improve search quality

---

### Phase 3: Advanced Features (6-12 months)

#### 3.1 Multi-Source Integration
**Target Users:** Enterprise customers  
**Description:** Index content from external sources (Confluence, Notion, Google Drive, SharePoint)

**User Story:**
> As an enterprise admin, I want to connect our Confluence wiki so that users can search all our documentation in one place.

**Supported Sources:**
- Confluence
- Notion
- Google Drive
- SharePoint
- Slack (channel history)
- GitHub (README, documentation)

**Value Proposition:**
- Centralized knowledge access
- Reduce tool-switching
- Comprehensive search across platforms

**LlamaIndex Features:**
- **Data Connectors:** Pre-built connectors for external sources
- **ConfluenceReader:** Confluence integration
- **NotionReader:** Notion integration
- **Google DriveReader:** Google Drive integration
- **Refresh/Update Tracking:** Incremental updates

---

#### 3.2 Conversational Context
**Target Users:** All users  
**Description:** Multi-turn conversations with context retention

**User Story:**
> As a user, I want to have a conversation with the AI assistant where it remembers previous questions so that I can ask follow-up questions naturally.

**Example:**
```
User: "How do I configure SSO?"
Assistant: "To configure SSO, you'll need to..."

User: "What about SAML specifically?"
Assistant: "For SAML SSO configuration specifically, you'll need to..."
```

**Technical Implementation:**
- Store conversation history (session-scoped)
- Include previous Q&A pairs in context
- Conversation memory per user session

**Value Proposition:**
- Natural conversation flow
- Deeper exploration of topics
- Better user experience

**LlamaIndex Features:**
- **Chat Engine:** Built-in conversational memory
- **Condense Plus Context Mode:** Context-aware follow-ups
- **Chat Memory Buffer:** Store conversation history

---

#### 3.3 Fuzzy Search & Typo Tolerance
**Target Users:** All users  
**Description:** Handle misspellings and typos gracefully

**Example:**
- "pasword reset" → finds "password reset"
- "refnd policy" → finds "refund policy"

**Technical Implementation:**
- Elasticsearch fuzzy matching
- Edit distance tolerance (1-2 characters)
- Phonetic matching (soundex/metaphone)

**Value Proposition:**
- Forgiving search experience
- Reduces user frustration
- Captures more queries successfully

---

#### 3.4 Advanced Filtering & Facets
**Target Users:** Power users  
**Description:** Filter search results by metadata (date, author, document type, tags)

**Filters:**
- Document type (PDF, DOCX, Wiki, etc.)
- Upload date range
- Uploaded by (user)
- Custom tags
- Document status

**Technical Implementation:**
- Elasticsearch aggregations
- Metadata extraction during indexing
- UI filter components

**Value Proposition:**
- Precise result filtering
- Better for large knowledge bases
- Improved discoverability

---

#### 3.5 Citation & Source Linking
**Target Users:** All users  
**Description:** Every AI answer includes clickable citations to source documents

**Example:**
```
Assistant: "Refunds are processed within 5-7 business days [1]. 
You'll need to contact support@example.com to initiate a refund [2]."

[1] Refund Policy (page 2)
[2] Customer Support Guide (page 5)
```

**Value Proposition:**
- Transparency and trust
- Verification of AI answers
- Quick access to full context

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│              (B2C API / B2B API / Platform)              │
└──────────────┬────────────────────┬─────────────────────┘
               │                    │
               │ Metadata           │ Search Queries
               │ Operations         │ + Indexing
               ↓                    ↓
    ┌──────────────────┐  ┌──────────────────────┐
    │   PostgreSQL     │  │   Elasticsearch      │
    │                  │  │                      │
    │  Tables:         │  │  Indexes:            │
    │  - documents     │  │  - chunks            │
    │  - queries       │  │    ├─ content (text) │
    │  - workspaces    │  │    ├─ embedding      │
    │  - tenants       │  │    ├─ tenant_id      │
    │                  │  │    ├─ workspace_id   │
    │                  │  │    └─ metadata       │
    └──────────────────┘  └──────────────────────┘
               │                    │
               └────────┬───────────┘
                        │
              ┌─────────▼─────────┐
              │  Redis (Broker)   │
              │  + Celery Workers │
              └───────────────────┘
               
    ┌─────────────────────────────────────────────────┐
    │         External Services (Pluggable)            │
    ├─────────────────────────────────────────────────┤
    │  LLM:     Azure OpenAI | OpenAI | Anthropic     │
    │           | Ollama (local)                       │
    │  Embeddings: OpenAI | Cohere | sentence-        │
    │              transformers (local)                │
    │  Storage: S3 | Azure Blob | MinIO (local)       │
    │  LlamaIndex (Document Processing)                │
    └─────────────────────────────────────────────────┘
```

### Data Flow

#### Document Ingestion
1. User uploads document → Save to object storage (via storage adapter)
2. Create `documents` record in PostgreSQL (status: processing)
3. Enqueue Celery task: `process_document.delay(document_id)`
4. Celery worker processes document:
   - Download from object storage (via storage adapter)
   - Parse with LlamaIndex (PDF, DOCX, TXT)
   - Chunk content (1024 chars, 20 overlap)
   - Generate embeddings (via embedding provider adapter)
   - Bulk index to Elasticsearch
5. Update `documents` status → completed

#### Query Processing
1. User submits query → Create `queries` record
2. Generate query embedding (via embedding provider adapter)
3. Hybrid search in Elasticsearch:
   - BM25 search (keyword matching)
   - Vector search (semantic similarity)
   - RRF fusion (combine rankings)
4. Build context prompt from top chunks
5. Generate answer (via LLM provider adapter)
6. Log query metadata → PostgreSQL
7. Return answer + citations to user

---

## Pluggable Provider Architecture

### Provider Abstraction Layer

To support multiple LLM, embedding, and storage providers, we'll implement adapter pattern:

**File:** `services/shared/adapters/llm_provider.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """Generate chat completion"""
        pass
    
    @abstractmethod
    async def generate_embedding(
        self,
        text: str
    ) -> List[float]:
        """Generate text embedding"""
        pass

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI implementation"""
    def __init__(self, api_key: str, endpoint: str, deployment_name: str):
        self.client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint)
        self.deployment = deployment_name
    
    async def generate_completion(self, prompt, **kwargs):
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
    
    async def generate_embedding(self, text):
        response = await self.client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        return response.data[0].embedding

class OllamaProvider(LLMProvider):
    """Ollama local LLM implementation"""
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = ollama.Client(host=base_url)
    
    async def generate_completion(self, prompt, **kwargs):
        response = self.client.chat(
            model="llama3.2",  # or mistral, phi, etc
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']
    
    async def generate_embedding(self, text):
        response = self.client.embeddings(
            model="nomic-embed-text",  # or mxbai-embed-large
            prompt=text
        )
        return response['embedding']
```

**File:** `services/shared/adapters/storage_provider.py`

```python
from abc import ABC, abstractmethod
from pathlib import Path

class StorageProvider(ABC):
    """Abstract base class for object storage"""
    
    @abstractmethod
    async def upload_file(
        self,
        file_path: Path,
        object_key: str
    ) -> str:
        """Upload file and return URL"""
        pass
    
    @abstractmethod
    async def download_file(
        self,
        object_key: str,
        dest_path: Path
    ) -> None:
        """Download file to local path"""
        pass
    
    @abstractmethod
    async def delete_file(self, object_key: str) -> None:
        """Delete file"""
        pass

class S3Provider(StorageProvider):
    """AWS S3 implementation"""
    def __init__(self, bucket: str, region: str):
        self.s3 = boto3.client('s3', region_name=region)
        self.bucket = bucket
    
    async def upload_file(self, file_path, object_key):
        self.s3.upload_file(str(file_path), self.bucket, object_key)
        return f"s3://{self.bucket}/{object_key}"
    
    async def download_file(self, object_key, dest_path):
        self.s3.download_file(self.bucket, object_key, str(dest_path))
    
    async def delete_file(self, object_key):
        self.s3.delete_object(Bucket=self.bucket, Key=object_key)

class MinIOProvider(StorageProvider):
    """MinIO local storage implementation"""
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False  # Use True for HTTPS
        )
        self.bucket = bucket
        # Create bucket if it doesn't exist
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
    
    async def upload_file(self, file_path, object_key):
        self.client.fput_object(self.bucket, object_key, str(file_path))
        return f"minio://{self.bucket}/{object_key}"
    
    async def download_file(self, object_key, dest_path):
        self.client.fget_object(self.bucket, object_key, str(dest_path))
    
    async def delete_file(self, object_key):
        self.client.remove_object(self.bucket, object_key)
```

**Provider Factory:**

```python
# services/shared/factories/provider_factory.py
from enum import Enum

class LLMProviderType(Enum):
    AZURE_OPENAI = "azure_openai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"  # Local development

class StorageProviderType(Enum):
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    MINIO = "minio"  # Local development

def get_llm_provider(provider_type: str = None) -> LLMProvider:
    """Factory to create LLM provider based on config"""
    provider_type = provider_type or settings.LLM_PROVIDER
    
    if provider_type == LLMProviderType.AZURE_OPENAI.value:
        return AzureOpenAIProvider(
            api_key=settings.AZURE_OPENAI_API_KEY,
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT
        )
    elif provider_type == LLMProviderType.OLLAMA.value:
        return OllamaProvider(base_url=settings.OLLAMA_BASE_URL)
    # ... other providers

def get_storage_provider(provider_type: str = None) -> StorageProvider:
    """Factory to create storage provider based on config"""
    provider_type = provider_type or settings.STORAGE_PROVIDER
    
    if provider_type == StorageProviderType.S3.value:
        return S3Provider(
            bucket=settings.S3_BUCKET,
            region=settings.AWS_REGION
        )
    elif provider_type == StorageProviderType.MINIO.value:
        return MinIOProvider(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET
        )
    # ... other providers
```

---

## Local Development Setup (Zero Cost)

### Overview

For local development, we can achieve zero-cost LLM and embedding by using open-source alternatives:

- **LLM:** Ollama with Llama 3.2, Mistral, or Phi models
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2 or all-mpnet-base-v2)
- **Object Storage:** MinIO (S3-compatible)
- **Elasticsearch:** Docker container
- **Redis:** Docker container
- **PostgreSQL:** Docker container

### Docker Compose for Local Development

**File:** `docker-compose.dev.yml` (add to existing)

```yaml
version: '3.8'

services:
  # ... existing services...
  
  # MinIO (S3-compatible object storage)
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"      # API
      - "9001:9001"      # Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
  
  # Elasticsearch (search engine)
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
  
  # Redis (Celery broker)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
  
  # Celery Worker
  celery_worker:
    build: .
    command: celery -A services.b2c.app.celery_app worker --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - LLM_PROVIDER=ollama
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - STORAGE_PROVIDER=minio
      - MINIO_ENDPOINT=minio:9000
      - ELASTICSEARCH_URL=http://elasticsearch:9200
    depends_on:
      - redis
      - elasticsearch
      - minio
    volumes:
      - .:/app

volumes:
  minio_data:
  es_data:
  redis_data:
```

### Ollama Setup (Local LLM)

**Installation:**

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com/download

# Start Ollama service
ollama serve
```

**Pull Models:**

```bash
# LLM for chat (choose one based on your hardware)
ollama pull llama3.2          # 2GB, good for most laptops
ollama pull mistral           # 4GB, better quality
ollama pull phi3              # 2.3GB, fast and efficient

# Embedding model
ollama pull nomic-embed-text  # 274MB, excellent embeddings
ollama pull mxbai-embed-large # 669MB, higher quality
```

**Test Ollama:**

```bash
# Test chat
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Hello!"}]
}'

# Test embeddings
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "Hello world"
}'
```

### sentence-transformers Setup (Alternative for Embeddings)

**Installation:**

```bash
pip install sentence-transformers
```

**Embedding Provider:**

```python
# services/shared/adapters/embedding_provider.py
from sentence_transformers import SentenceTransformer

class SentenceTransformerProvider:
    """Local embedding with sentence-transformers"""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Downloads ~80MB model first time
        self.model = SentenceTransformer(model_name)
    
    async def generate_embedding(self, text: str) -> List[float]:
        # Returns 384-dimensional vector (adjust ES index accordingly)
        embedding = self.model.encode(text)
        return embedding.tolist()
```

**Recommended Models:**

| Model | Dimensions | Size | Speed | Quality |
|-------|------------|------|-------|---------|
| all-MiniLM-L6-v2 | 384 | 80MB | ⚡️ Fast | Good |
| all-mpnet-base-v2 | 768 | 420MB | Medium | Better |
| BAAI/bge-small-en-v1.5 | 384 | 125MB | Fast | Good |

### Environment Configuration

**File:** `.env.local`

```bash
# LLM Provider
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Storage Provider
STORAGE_PROVIDER=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documents
MINIO_USE_SSL=false

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=chunks

# Celery/Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# PostgreSQL (existing)
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

**File:** `.env.production`

```bash
# LLM Provider
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# Storage Provider
STORAGE_PROVIDER=s3
AWS_S3_BUCKET=your-bucket
AWS_REGION=us-east-1

# ... other production configs
```

### Local Development Workflow

**1. Start Infrastructure:**

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Check health
docker-compose ps
```

**2. Start Ollama (in separate terminal):**

```bash
ollama serve
```

**3. Run Migrations:**

```bash
# Create Elasticsearch index
python scripts/create_es_index.py

# Run DB migrations
alembic upgrade head
```

**4. Start Celery Worker:**

```bash
celery -A services.b2c.app.celery_app worker --loglevel=info
```

**5. Start API Server:**

```bash
cd services/b2c
uvicorn app.main:app --reload --port 8000
```

**6. Test Document Upload:**

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf"
```

### Cost Comparison

| Component | Production | Local Dev | Savings |
|-----------|-----------|-----------|---------|
| LLM | Azure OpenAI $100/mo | Ollama $0 | $100/mo |
| Embeddings | OpenAI $50/mo | Ollama/sentence-transformers $0 | $50/mo | 
| Object Storage | S3 $30/mo | MinIO $0 | $30/mo |
| **Total** | **$180/mo** | **$0** | **$180/mo** |

**Hardware Requirements for Local Dev:**
- RAM: 8GB minimum (16GB recommended for larger models)
- Disk: 10GB for models + document storage
- CPU: Any modern CPU works (Apple Silicon preferred for Ollama)


---

## Feature Roadmap

### Phase 1: MVP (Months 1-3)

**Goal:** Launch basic RAG functionality for early adopters

| Feature | Priority | Effort | Dependencies |
|---------|----------|--------|--------------|
| Document upload (PDF, TXT) | P0 | 3w | Object storage setup |
| Elasticsearch setup | P0 | 2w | Infrastructure |
| PostgreSQL schema | P0 | 1w | Migration system |
| Basic hybrid search | P0 | 3w | ES + embeddings |
| Q&A interface | P0 | 2w | Frontend components |
| Tenant isolation | P0 | 1w | Auth system |
| Admin document management | P1 | 2w | Admin UI |
| Basic analytics (query logs) | P1 | 1w | PostgreSQL queries |

**Deliverable:** Working RAG system for single tenant use case

---

### Phase 2: Enhanced (Months 4-6)

**Goal:** Add workspace support and improve search quality

| Feature | Priority | Effort | Dependencies |
|---------|----------|--------|--------------|
| Workspace-scoped knowledge | P0 | 2w | Workspace system |
| DOCX support | P1 | 1w | LlamaIndex parser |
| Query suggestions | P1 | 2w | Elasticsearch completions |
| Analytics dashboard | P1 | 3w | Data visualization |
| Search filters | P2 | 2w | ES aggregations |
| Relevance tuning | P1 | 1w | ES scoring |

**Deliverable:** Production-ready system with workspace isolation

---

### Phase 3: Advanced (Months 7-12)

**Goal:** Enterprise features and integrations

| Feature | Priority | Effort | Dependencies |
|---------|----------|--------|--------------|
| Confluence integration | P1 | 4w | OAuth setup |
| Notion integration | P1 | 3w | API integration |
| Google Drive integration | P2 | 3w | OAuth setup |
| Conversational context | P1 | 2w | Session management |
| Fuzzy search | P1 | 1w | ES configuration |
| Citation linking | P0 | 2w | Document parsing |
| Advanced filters | P2 | 2w | Metadata extraction |
| Synonym support | P2 | 1w | ES synonym config |
| Multi-language | P2 | 3w | Language detection |

**Deliverable:** Enterprise-grade RAG platform

---

## Implementation Phases

### Phase 1: Foundation (Months 1-3)

#### Milestone 1.1: Infrastructure Setup (Week 1-2)

**Tasks:**
1. **Elasticsearch Cluster Setup**
   - Provision 3-node cluster (AWS OpenSearch or Elastic Cloud)
   - Configure security (TLS, authentication)
   - Set up index templates
   - Create monitoring alerts

2. **RabbitMQ Setup**
   - Provision message queue instance
   - Configure queues: `document.processing`, `document.indexing`
   - Set up dead letter queues for failures
   - Configure monitoring

3. **Object Storage**
   - Create S3 bucket (or Azure Blob container)
   - Set up lifecycle policies
   - Configure access policies (tenant-scoped)

4. **Azure OpenAI Setup**
   - Create Azure OpenAI resource
   - Deploy embedding model: `text-embedding-3-large`
   - Deploy chat model: `gpt-4` or `gpt-4-turbo`
   - Set up rate limiting and quotas

**Success Criteria:**
- ✅ Elasticsearch cluster accessible and healthy
- ✅ RabbitMQ processing test messages
- ✅ Object storage accepting uploads
- ✅ Azure OpenAI responding to API calls

---

#### Milestone 1.2: Database Schema (Week 2-3)

**PostgreSQL Schema:**

```sql
-- Documents table (metadata only)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    workspace_id UUID REFERENCES workspaces(id),
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    storage_url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL, -- processing, completed, failed
    chunk_count INTEGER DEFAULT 0,
    error_message TEXT,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    indexed_at TIMESTAMP
);

CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_workspace ON documents(workspace_id);
CREATE INDEX idx_documents_status ON documents(status);

-- Queries table (analytics)
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    workspace_id UUID REFERENCES workspaces(id),
    user_id UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    response_text TEXT,
    retrieved_chunk_ids TEXT[], -- Array of Elasticsearch doc IDs
    execution_time_ms INTEGER,
    satisfaction_rating SMALLINT, -- 1-5 stars
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_queries_tenant ON queries(tenant_id);
CREATE INDEX idx_queries_workspace ON queries(workspace_id);
CREATE INDEX idx_queries_created_at ON queries(created_at DESC);
```

**Elasticsearch Index Mapping:**

```json
{
  "mappings": {
    "properties": {
      "chunk_id": {"type": "keyword"},
      "document_id": {"type": "keyword"},
      "tenant_id": {"type": "keyword"},
      "workspace_id": {"type": "keyword"},
      "content": {
        "type": "text",
        "analyzer": "standard"
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 3072,
        "index": true,
        "similarity": "cosine"
      },
      "chunk_index": {"type": "integer"},
      "metadata": {
        "properties": {
          "filename": {"type": "keyword"},
          "page_number": {"type": "integer"},
          "section_title": {"type": "text"}
        }
      },
      "created_at": {"type": "date"}
    }
  },
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1
  }
}
```

**Success Criteria:**
- ✅ Migrations applied successfully
- ✅ Elasticsearch index created
- ✅ Sample data inserts working

---

#### Milestone 1.3: Document Ingestion Pipeline (Week 3-5)

**Components:**

1. **Document Upload API**
   ```python
   POST /api/v1/documents/upload
   Content-Type: multipart/form-data
   
   Required: file, workspace_id (optional)
   Returns: document_id, status
   ```

2. **Document Processor Service**
   - Listen to RabbitMQ queue
   - Download file from object storage
   - Parse with LlamaIndex
   - Chunk content (SentenceSplitter)
   - Generate embeddings (batch processing)
   - Index to Elasticsearch (bulk API)
   - Update PostgreSQL status

3. **Error Handling**
   - Retry logic (exponential backoff)
   - Dead letter queue for failures
   - Error logging and alerts
   - Status updates to PostgreSQL

**Success Criteria:**
- ✅ PDF upload completes successfully
- ✅ Document appears in Elasticsearch
- ✅ Chunks searchable within 60 seconds
- ✅ Failed documents logged with error message

---

#### Milestone 1.4: Hybrid Search Implementation (Week 5-7)

**Search API:**

```python
POST /api/v1/search/query
{
  "query": "How do I reset my password?",
  "workspace_id": "uuid" (optional),
  "top_k": 5,
  "include_citations": true
}

Response:
{
  "query_id": "uuid",
  "answer": "To reset your password...",
  "citations": [
    {
      "document_id": "uuid",
      "filename": "User Guide.pdf",
      "chunk_index": 12,
      "score": 0.89,
      "snippet": "...process for password reset..."
    }
  ],
  "execution_time_ms": 245
}
```

**Implementation:**

1. **Vector Search**
   - Generate query embedding
   - Elasticsearch kNN query
   - Filter by tenant_id + workspace_id
   - Return top 10 candidates

2. **BM25 Search**
   - Elasticsearch match query
   - Same tenant/workspace filter
   - Return top 10 candidates

3. **RRF Fusion**
   - Combine rankings (k=60)
   - Return top 5 fused results

4. **Context Building**
   - Format chunks into prompt
   - Add system instructions
   - Include conversation history (future)

5. **Answer Generation**
   - Call Azure OpenAI Chat API
   - Stream response to user
   - Extract citations

**Success Criteria:**
- ✅ Search returns results in <500ms
- ✅ Answers are accurate and relevant
- ✅ Citations link to correct documents
- ✅ Tenant isolation enforced

---

#### Milestone 1.5: Frontend Interface (Week 7-9)

**UI Components:**

1. **Document Management Page**
   - Upload button
   - Document list (table view)
   - Status badges (processing, completed, failed)
   - Delete/download actions
   - Filter by status, date

2. **Search Interface**
   - Search input with auto-focus
   - Loading states
   - Answer display (markdown rendering)
   - Citation chips (clickable)
   - Feedback buttons (thumbs up/down)

3. **Admin Analytics**
   - Query count (today, week, month)
   - Top queries table
   - Document count
   - Average latency chart

**Success Criteria:**
- ✅ Users can upload documents
- ✅ Users can search and get answers
- ✅ Admins can view analytics
- ✅ UI is responsive and intuitive

---

### Phase 2: Enhanced Features (Months 4-6)

#### Milestone 2.1: Workspace Isolation (Week 10-11)

**Changes Required:**

1. **Extend Elasticsearch Filtering**
   - Add workspace_id to all queries
   - Update bulk indexing to include workspace_id
   - Reindex existing documents

2. **API Updates**
   - Make workspace_id optional (defaults to user's current workspace)
   - Add workspace switcher to UI
   - Update permissions (workspace-level access)

3. **Migration**
   - Add workspace_id to documents table
   - Backfill workspace_id for existing documents
   - Update indexes

**Success Criteria:**
- ✅ Users only see their workspace's documents
- ✅ Search scoped to current workspace
- ✅ No cross-workspace data leaks

---

#### Milestone 2.2: Enhanced Document Support (Week 11-12)

**Parsers to Add:**

1. **DOCX Parser**
   - Use python-docx or LlamaIndex
   - Extract text, tables, images (OCR)
   - Preserve formatting metadata

2. **Markdown Parser**
   - Native LlamaIndex support
   - Preserve headers, code blocks
   - Extract links

3. **HTML Parser**
   - BeautifulSoup or LlamaIndex
   - Clean unnecessary tags
   - Extract main content

**Success Criteria:**
- ✅ DOCX files indexed correctly
- ✅ Markdown formatting preserved
- ✅ HTML content cleaned and indexed

---

#### Milestone 2.3: Query Analytics Dashboard (Week 13-15)

**Metrics:**

1. **Query Volume**
   - Queries per day/week/month
   - Unique vs repeat queries
   - Peak usage times

2. **Query Quality**
   - Queries with no results
   - Low confidence answers (<0.5 score)
   - User satisfaction ratings

3. **Document Performance**
   - Most cited documents
   - Least used documents
   - Documents with errors

4. **System Performance**
   - Average query latency (p50, p95, p99)
   - Indexing throughput
   - Error rates

**Visualization:**
- Line charts (time series)
- Bar charts (top queries, documents)
- Tables (sortable, filterable)
- Export to CSV

**Success Criteria:**
- ✅ Dashboard loads in <2 seconds
- ✅ Real-time updates (or 5-min cache)
- ✅ Actionable insights visible

---

### Phase 3: Advanced Features (Months 7-12)

#### Milestone 3.1: External Integrations (Week 16-20)

**Confluence Integration:**

1. **OAuth Setup**
   - Register OAuth app with Atlassian
   - Handle authorization flow
   - Store refresh tokens securely

2. **Content Sync**
   - Periodic sync (daily/weekly)
   - Fetch pages via REST API
   - Extract content (markdown conversion)
   - Track sync status

3. **Change Detection**
   - Monitor page updates
   - Re-index modified pages
   - Delete removed pages

**Similar patterns for Notion, Google Drive, SharePoint**

**Success Criteria:**
- ✅ Users can connect their Confluence space
- ✅ Pages synced within 24 hours
- ✅ Updates detected and re-indexed

---

#### Milestone 3.2: Conversational Context (Week 20-22)

**Implementation:**

1. **Session Management**
   - Store conversation history
   - Session expiration (1 hour idle)
   - Clear session button

2. **Context Inclusion**
   - Include previous 2-3 Q&A pairs
   - Truncate if too long
   - Smart context pruning

3. **API Updates**
   - Add session_id to query request
   - Return conversation_id
   - Conversation history endpoint

**Success Criteria:**
- ✅ Follow-up questions work naturally
- ✅ Context doesn't degrade answer quality
- ✅ Sessions expire appropriately

---

#### Milestone 3.3: Advanced Search Features (Week 22-24)

**Fuzzy Search:**
- Enable Elasticsearch fuzziness
- Configure edit distance (auto)
- Test with common typos

**Synonym Support:**
- Build synonym dictionary
- Configure ES synonym filter
- Test with domain-specific terms

**Faceted Search:**
- Implement filters UI
- Add ES aggregations
- Cache filter counts

**Success Criteria:**
- ✅ Typos handled gracefully
- ✅ Synonyms improve recall
- ✅ Filters reduce result set effectively

---

## Advanced Features Timeline

### When to Introduce Each Feature

| Feature | Timing | Trigger Signal | Complexity |
|---------|--------|----------------|------------|
| **Workspace isolation** | Month 4 | B2C users requesting multi-workspace | Medium |
| **DOCX support** | Month 4 | User requests for Office docs | Low |
| **Query analytics** | Month 5 | 1000+ queries/month | Medium |
| **Search suggestions** | Month 5 | Users re-typing similar queries | Medium |
| **Confluence integration** | Month 7 | Enterprise customers asking | High |
| **Conversational context** | Month 8 | Users asking follow-up questions | Medium |
| **Fuzzy search** | Month 9 | 10%+ queries with typos | Low |
| **Citation linking** | Month 10 | Users requesting source verification | Medium |
| **Multi-language** | Month 11 | International customers | High |
| **Advanced filters** | Month 12 | 10K+ documents indexed | Medium |

### Decision Criteria for Advanced Features

**Introduce feature when:**
1. ✅ At least 3 customers explicitly request it
2. ✅ Foundation is stable (>99% uptime)
3. ✅ Team has bandwidth (not in crisis mode)
4. ✅ ROI is clear (revenue impact or churn prevention)

**Delay feature when:**
1. ❌ <100 active users
2. ❌ Core features have bugs
3. ❌ Infrastructure costs already high
4. ❌ Low usage of related features

---

## Cost & Resource Planning

### Infrastructure Costs (Monthly)

**Small Scale (<1000 users, <10K documents):**

| Service | Configuration | Cost |
|---------|--------------|------|
| Elasticsearch | 3-node cluster (t3.medium) | $300 |
| RabbitMQ | Single instance (t3.small) | $40 |
| PostgreSQL | db.r6g.large | $175 |
| Object Storage | 100GB + egress | $30 |
| Azure OpenAI | 1M tokens/month | $100 |
| **Total** | | **$645/month** |

**Medium Scale (1K-10K users, 10K-100K documents):**

| Service | Configuration | Cost |
|---------|--------------|------|
| Elasticsearch | 3-node cluster (r6g.xlarge) | $600 |
| RabbitMQ | HA cluster (2x t3.medium) | $120 |
| PostgreSQL | db.r6g.xlarge | $350 |
| Object Storage | 1TB + egress | $100 |
| Azure OpenAI | 10M tokens/month | $800 |
| **Total** | | **$1,970/month** |

**Large Scale (>10K users, >100K documents):**

| Service | Configuration | Cost |
|---------|--------------|------|
| Elasticsearch | 5-node cluster (r6g.2xlarge) | $1,500 |
| RabbitMQ | HA cluster (3x t3.large) | $240 |
| PostgreSQL | db.r6g.2xlarge | $700 |
| Object Storage | 5TB + egress | $400 |
| Azure OpenAI | 50M tokens/month | $3,500 |
| **Total** | | **$6,340/month** |

### Development Resources

**Phase 1 (3 months):**
- 1x Backend Engineer (full-time)
- 1x Frontend Engineer (full-time)
- 0.5x DevOps Engineer
- 0.25x Product Manager

**Phase 2-3 (6-9 months):**
- 1x Backend Engineer (full-time)
- 0.5x Frontend Engineer
- 0.25x DevOps Engineer
- 0.25x Product Manager

---

## Success Metrics

### North Star Metrics

1. **Query Success Rate:** % of queries that return relevant answers
   - Target: >80% by Month 3, >90% by Month 6

2. **User Adoption:** % of active users who use RAG feature
   - Target: >40% by Month 6, >60% by Month 12

3. **Time to Answer:** Average time from question to answer
   - Target: <10 seconds initially, <5 seconds by Month 6

### Product Metrics

| Metric | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|----------|
| Total queries | 1,000 | 10,000 | 50,000 |
| Documents indexed | 500 | 5,000 | 25,000 |
| Average query latency | <500ms | <300ms | <200ms |
| User satisfaction | >3.5/5 | >4.0/5 | >4.5/5 |
| Query success rate | >80% | >85% | >90% |

### Technical Metrics

1. **Availability:** >99.5% uptime
2. **Search Latency:**
   - p50: <200ms
   - p95: <500ms
   - p99: <1s

3. **Indexing Throughput:** >100 docs/hour
4. **Error Rate:** <1% of queries/indexing jobs

### Business Metrics

1. **Support Ticket Deflection:** 20% reduction by Month 6
2. **User Engagement:** +15% DAU/MAU ratio
3. **Feature Stickiness:** >50% weekly active RAG users
4. **Revenue Impact:** Enable upsell to Enterprise tier

---

## Appendix

### Technology Stack Summary

| Component | Production | Local Development | Rationale |
|-----------|-----------|-------------------|-----------|
| Search Engine | Elasticsearch 8.x | Elasticsearch (Docker) | Best-in-class search, native hybrid support |
| Database | PostgreSQL 15+ | PostgreSQL (Docker) | Metadata, analytics, tenant data |
| Task Queue | Celery 5.x + Redis | Celery + Redis (Docker) | Reliable async processing, Python native |
| Object Storage | S3 / Azure Blob | MinIO | Scalable document storage |
| Embeddings | OpenAI / Azure OpenAI | Ollama / sentence-transformers | Pluggable, quality embeddings |
| LLM | GPT-4 / Claude | Ollama (Llama3.2, Mistral) | Pluggable, best quality |
| Document Processing | LlamaIndex | LlamaIndex | Rich parser ecosystem, advanced routing |
| Backend | Python 3.11+ FastAPI | Same | Existing stack |
| Frontend | React | Same | Existing stack |

### Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Elasticsearch costly at scale | High | Monitor costs, optimize index settings, consider compression |
| Azure OpenAI rate limits | High | Implement caching, batch processing, fallback to other providers |
| Poor search quality | High | Continuous tuning, user feedback loop, A/B testing |
| Data synchronization issues | Medium | Robust retry logic, monitoring, dead letter queues |
| Tenant isolation breach | Critical | Strict filtering, security audits, penetration testing |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | System | Initial specification |

