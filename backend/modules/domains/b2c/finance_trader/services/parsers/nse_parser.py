import logging
from typing import List, Sequence, Optional, Dict, Any
import re
from pathlib import Path

from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import BaseNode, Document, TextNode
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser
from llama_index.core.bridge.pydantic import Field, PrivateAttr

logger = logging.getLogger(__name__)

class NSEEarningsParser(NodeParser):
    """
    Parser specialized for NSE Earnings Reports and Transcripts.
    Phase 2 Implementation:
    - PDF: Extracts tables using pdfplumber and converts to Markdown.
    - Transcript: Segments text by speaker (Management/Analyst/Operator).
    """
    chunk_size: int = Field(default=1024, description="Chunk size")
    chunk_overlap: int = Field(default=20, description="Chunk overlap")
    _splitter: NodeParser = PrivateAttr()
    _pdf_strategy: Any = PrivateAttr() # Type hint Any to avoid pydantic validation issues with Abstract class

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 20, pdf_strategy = None, embed_model = None, **kwargs):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)
        
        # Use Semantic Splitter if embed_model is provided
        if embed_model:
            from llama_index.core.node_parser import SemanticSplitterNodeParser
            # buffer_size=1 means it processes sentences one by one for breakpoints
            # breakpoint_percentile_threshold=95 means it splits when similarity drops significantly (top 5% of drops)
            self._splitter = SemanticSplitterNodeParser(
                buffer_size=1, 
                breakpoint_percentile_threshold=95, 
                embed_model=embed_model
            )
            # We still keep a sentence splitter for fallback/size checks if needed, but primary is semantic
        else:
            self._splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # Default Strategy if not provided
        if pdf_strategy is None:
            from modules.domains.b2c.finance_trader.services.parsers.strategies import DoclingParsingStrategy
            # Enable Accurate Mode for better table extraction
            self._pdf_strategy = DoclingParsingStrategy(fast_mode=False, do_ocr=True)
        else:
            self._pdf_strategy = pdf_strategy

    def _parse_nodes(self, nodes: Sequence[BaseNode], show_progress: bool = False, **kwargs) -> List[BaseNode]:
        """
        Takes list of documents/nodes and turns them into parsed nodes.
        """
        all_nodes = []
        processed_files = set()

        for node in nodes:
            if isinstance(node, Document):
                # Check metadata for file path to handle PDFs specifically
                file_path = node.metadata.get("file_path")
                
                if file_path and file_path.lower().endswith(".pdf"):
                    # Deduplication: Docling parses the FULL file. 
                    # Only run it once per unique file path in this batch.
                    if file_path in processed_files:
                        continue
                    
                    parsed_nodes = self._parse_pdf(node)
                    processed_files.add(file_path)
                elif self._is_transcript(node.text):
                    parsed_nodes = self._parse_transcript(node)
                else:
                    # Fallback to standard splitting
                    parsed_nodes = self._splitter.get_nodes_from_documents([node], show_progress=show_progress)
                
                all_nodes.extend(parsed_nodes)
            else:
                # If it's already a TextNode, just split it further if needed
                all_nodes.extend(self._splitter.get_nodes_from_documents([node], show_progress=show_progress))
                
        return all_nodes

    def get_nodes_from_documents(self, documents: Sequence[Document], show_progress: bool = False, **kwargs) -> List[BaseNode]:
        return self._parse_nodes(documents, show_progress=show_progress, **kwargs)

    def _is_transcript(self, text: str) -> bool:
        """Heuristic to check if text looks like a transcript"""
        # Look for typical keywords in first 2000 chars
        header = text[:2000].lower()
        keywords = ["earnings call", "conference call", "transcript", "analyst", "operator", "management"]
        matches = sum(1 for k in keywords if k in header)
        return matches >= 2

    def _parse_pdf(self, doc: Document) -> List[BaseNode]:
        """
        Parse PDF using the configured strategy (e.g., Docling).
        Falls back to standard splitting on failure.
        """
        try:
            return self._pdf_strategy.parse(doc, self._splitter)
        except Exception as e:
            logger.error(f"Strategy parsing failed: {e}. Falling back to standard splitting.")
            return self._splitter.get_nodes_from_documents([doc])

    def _parse_transcript(self, doc: Document) -> List[BaseNode]:
        """
        Segment transcript by speaker.
        """
        text = doc.text
        # Regex to find "Speaker Name:" pattern
        # Assumption: Speaker names are often in Uppercase or clear delimiters
        # This is a naive heuristic
        
        # Split by known roles if present
        segments = re.split(r'\n(Operator|Management|Analyst|Moderator):', text)
        
        if len(segments) < 2:
            return self._splitter.get_nodes_from_documents([doc])
            
        nodes = []
        current_role = "Intro"
        
        for segment in segments:
            if segment in ["Operator", "Management", "Analyst", "Moderator"]:
                current_role = segment
                continue
            
            content = segment.strip()
            if not content:
                continue
                
            # Create a node for this segment
            node = TextNode(text=content, metadata={**doc.metadata, "speaker_role": current_role})
            nodes.append(node)
            
        return nodes
