import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from modules.domains.core.services.base_rag_service import BaseRagService
from modules.domains.nse.services.parsers.nse_parser import NSEEarningsParser

logger = logging.getLogger(__name__)

class RagService(BaseRagService):
    """
    NSE Domain Specific RAG Service.
    Extends BaseRagService to provide NSE-specific parser and configuration.
    """
    
    def __init__(self, index_name: str = "rag_documents"):
        super().__init__()
        self._index_name = index_name

    def get_index_name(self) -> str:
        return self._index_name

    def get_parser(self):
        return NSEEarningsParser()

# Singleton instance
rag_service = RagService()
