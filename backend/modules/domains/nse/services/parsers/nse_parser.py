import logging
from typing import List, Sequence, Optional, Dict, Any
import re
from pathlib import Path

from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import BaseNode, Document, TextNode
from llama_index.core.node_parser import SentenceSplitter
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
    _splitter: SentenceSplitter = PrivateAttr()
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 20, **kwargs):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs)
        self._splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def _parse_nodes(self, nodes: Sequence[BaseNode], show_progress: bool = False, **kwargs) -> List[BaseNode]:
        """
        Takes list of documents/nodes and turns them into parsed nodes.
        """
        all_nodes = []
        for node in nodes:
            if isinstance(node, Document):
                # Check metadata for file path to handle PDFs specifically
                file_path = node.metadata.get("file_path")
                if file_path and file_path.lower().endswith(".pdf"):
                    parsed_nodes = self._parse_pdf(node)
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
        Parse PDF using pdfplumber to extract text and tables separately.
        Standard text is chunked via SentenceSplitter.
        Tables are preserved as distinct TextNodes to maintain structure.
        """
        import pdfplumber
        
        file_path = doc.metadata.get("file_path")
        if not file_path:
            return self._splitter.get_nodes_from_documents([doc])

        nodes = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # 1. Extract and Process Text
                    # We accept that extract_text might still include some table gibberish, 
                    # but we rely on the Table Node to provide the clean version.
                    # A robust solution would use crop() to exclude tables, but that's complex.
                    text = page.extract_text() or ""
                    
                    if text.strip():
                        # Create temporary doc for this page's text and split it
                        page_doc = Document(text=text, metadata=doc.metadata)
                        page_text_nodes = self._splitter.get_nodes_from_documents([page_doc])
                        nodes.extend(page_text_nodes)

                    # 2. Extract and Process Tables
                    tables = page.extract_tables()
                    
                    # Fallback: If no tables found, try text-based strategy (whitespace)
                    if not tables:
                         logger.debug(f"[NSE Parser] Page {page.page_number}: No tables found with default strategy. Retrying with text strategy...")
                         tables = page.extract_tables(table_settings={
                             "vertical_strategy": "text", 
                             "horizontal_strategy": "text",
                             "snap_tolerance": 3,
                         })

                    logger.info(f"[NSE Parser] Page {page.page_number}: Found {len(tables)} tables")
                    
                    if tables:
                        # Strategy Change: Merge primary table into the first TextNode of the page.
                        # This ensures the node that ranks well (due to text content) also carries the UI payload.
                        
                        # We process the first table as the "Main" table for this page/chunk
                        table = tables[0]
                        
                        cleaned_table = [[str(cell or "").replace("\n", " ").strip() for cell in row] for row in table]
                        
                        # Skip if empty
                        if cleaned_table and any(any(c for c in row) for row in cleaned_table):
                            headers = cleaned_table[0]
                            
                            # Create Markdown for searchability
                            markdown_table = f"\n| {' | '.join(headers)} |\n| {' | '.join(['---']*len(headers))} |\n"
                            for row in cleaned_table[1:]:
                                markdown_table += f"| {' | '.join(row)} |\n"
                                
                            if page_text_nodes:
                                target_node = page_text_nodes[0]
                                logger.info(f"[NSE Parser] Merging Table {0} into TextNode {target_node.node_id[:8]}...")
                                
                                # Enrich Metadata
                                target_node.metadata.update({
                                    "is_table": True,
                                    "table_rows": len(cleaned_table),
                                    "table_columns": len(headers),
                                    "table_json": {
                                        "headers": headers,
                                        "rows": cleaned_table[1:]
                                    }
                                })
                                
                                # Append Markdown to text to ensure table structure is indexed
                                # We prepend a separator
                                target_node.text += f"\n\n--- TABLE DATA ---\n{markdown_table}"
                                
                        # If there are more tables, we could append them as text or log them.
                        # For now, focusing on the primary table per page avoids UI complexity.
                        if len(tables) > 1:
                            logger.debug(f"[NSE Parser] Page {page.page_number} has {len(tables)-1} extra tables, skipping JSON for them.")
                            
            return nodes
                            
            return nodes
            
        except Exception as e:
            # Fallback if pdfplumber fails
            logger.error(f"Error parsing PDF with pdfplumber: {e}")
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
