from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import logging

from llama_index.llms.openai import OpenAI
from llama_index.core.program import LLMTextCompletionProgram

logger = logging.getLogger(__name__)

class NSEScope(str, Enum):
    STANDALONE = "Standalone"
    CONSOLIDATED = "Consolidated"
    UNKNOWN = "Unknown"

class NSEReportType(str, Enum):
    EARNINGS = "earnings"
    CONCALL = "concall"
    ANNUAL_REPORT = "annual_report"
    UNKNOWN = "unknown"

class NSEDocumentMetadata(BaseModel):
    """
    Structured metadata extracted from the first page of an NSE Earnings/Financial document.
    """
    ticker: Optional[str] = Field(default=None, description="The NSE ticker symbol of the company, e.g. TCS, INFY, HDFCBANK. If not found, leave null.")
    company_name: Optional[str] = Field(default=None, description="The full name of the company.")
    fiscal_year: Optional[str] = Field(default=None, description="The Fiscal Year mentioned, normalized to format 'FY25', 'FY24'.")
    quarter: Optional[str] = Field(default=None, description="The Quarter mentioned, normalized to 'Q1', 'Q2', 'Q3', 'Q4'.")
    report_type: Optional[NSEReportType] = Field(default=None, description="The type of document: 'earnings' (Financial Results/Presentation) or 'concall' (Earnings Call Transcript).")
    scope: Optional[List[NSEScope]] = Field(default=None, description="The scope of financial results detected (Standalone, Consolidated, or both).")

class MetadataExtractor:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.llm = OpenAI(model=model, temperature=0.0)
    
    def extract(self, text: str) -> NSEDocumentMetadata:
        """
        Extracts metadata from the provided text (usually the first page).
        """
        try:
            # We use a simple prompt to extract the Pydantic model
            prompt_template_str = (
                "You are an expert financial analyst. Analyze the following text cover page "
                "from an Indian NSE listed company's financial report or earnings call.\n"
                "Extract the metadata items strictly.\n\n"
                "Canonicalization Rules:\n"
                "- Map 'HDFC', 'HDFC Limited', 'Housing Development Finance Corp' -> 'HDFCBANK' (as they are merged).\n"
                "- Map 'Reliance', 'RIL' -> 'RELIANCE'.\n"
                "- Map 'TCS', 'Tata Consultancy Services' -> 'TCS'.\n"
                "- Detect Report Type: 'Earnings' if it contains financial tables/results, 'Concall' if it is a transcript of a call.\n\n"
                "Text:\n{text}\n\n"
            )
            
            program = LLMTextCompletionProgram.from_defaults(
                output_cls=NSEDocumentMetadata,
                prompt_template_str=prompt_template_str,
                llm=self.llm,
                verbose=True
            )
            
            # Truncate text to avoid token limits, first 2-3k chars usually enough for cover page
            safe_text = text[:3000]
            
            logger.info(f"[MetadataExtractor] Analyzing Text (First 500 chars):\n{safe_text[:500]}...")
            
            completion = program(text=safe_text)
            logger.info(f"[MetadataExtractor] Extracted: {completion}")
            return completion
            
        except Exception as e:
            logger.error(f"[MetadataExtractor] Failed to extract metadata: {e}")
            # Return empty metadata on failure to not block pipeline
            return NSEDocumentMetadata(scope=[])
