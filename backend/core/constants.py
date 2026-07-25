"""
Application Constants
"""
from enum import Enum


class B2BRoleName:
    """
    Role slugs used in code logic.
    These must match the 'name' column in the roles table.
    """ 
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PlatformRoleName:
    """
    Role slugs used in code logic.
    These must match the 'name' column in the roles table.
    """ 
    PLATFORM_ADMIN = "platform_admin"
    SUPPORT_STAFF = "support_staff"
    BILLING_MANAGER = "billing_manager"


# NSE Domain Constants

class DocumentStatus(str, Enum):
    """RAG document ingestion status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportType(str, Enum):
    """NSE financial report types."""
    EARNINGS = "earnings"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    TRANSCRIPT = "transcript"


class RAGDefaults:
    """Default configuration values for RAG operations."""
    # Retrieval Settings
    VECTOR_TOP_K = 50
    BM25_TOP_K = 50
    FUSION_TOP_K = 30
    RERANK_TOP_K = 5
    
    # Retriever Weights
    VECTOR_WEIGHT = 0.5
    BM25_WEIGHT = 0.5
    
    # Parsing Settings
    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 20
    METADATA_PAGES_TO_SCAN = 3
    
    # Upload Limits
    MAX_FILE_SIZE_MB = 50
    STORAGE_BUCKET = "rag-documents"

