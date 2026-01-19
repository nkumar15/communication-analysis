"""
NSE Domain Custom Exceptions

Custom exception classes for NSE RAG operations.
"""


class RAGException(Exception):
    """Base exception for RAG operations."""
    pass


class DocumentUploadError(RAGException):
    """Error during document upload."""
    pass


class IngestionError(RAGException):
    """Error during document ingestion."""
    pass


class SearchError(RAGException):
    """Error during search operation."""
    pass


class MetadataExtractionError(RAGException):
    """Error during metadata extraction."""
    pass


class SynthesisError(RAGException):
    """Error during answer synthesis."""
    pass
