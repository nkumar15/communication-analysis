from typing import List, Sequence, Optional, Dict, Any
import re
from pathlib import Path

from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import BaseNode, Document, TextNode
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.bridge.pydantic import Field, PrivateAttr

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
        Parse PDF using pdfplumber to extract tables and text.
        Returns a list of TextNodes, with tables as Markdown.
        """
        import pdfplumber
        
        file_path = doc.metadata.get("file_path")
        if not file_path:
            return self._splitter.get_nodes_from_documents([doc])

        nodes = []
        full_text = ""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract tables
                    tables = page.extract_tables()
                    text = page.extract_text() or ""
                    
                    # If tables exist, convert to markdown
                    if tables:
                        for table in tables:
                            # Basic Markdown Table conversion
                            # Filter None/Empty values
                            cleaned_table = [[str(cell or "").replace("\n", " ") for cell in row] for row in table]
                            if not cleaned_table:
                                continue
                                
                            # Create Header
                            headers = cleaned_table[0]
                            markdown_table = f"\n\n| {' | '.join(headers)} |\n| {' | '.join(['---']*len(headers))} |\n"
                            for row in cleaned_table[1:]:
                                markdown_table += f"| {' | '.join(row)} |\n"
                            markdown_table += "\n"
                            
                            # Append table to text (naive placement at end of page text, 
                            # ideally we replace the area, but typical for RAG just appending works for context)
                            text += markdown_table
                    
                    full_text += text + "\n\n"
                    
            # Now split the enriched text
            # Create a temporary document with the new full_text
            temp_doc = Document(text=full_text, metadata=doc.metadata)
            return self._splitter.get_nodes_from_documents([temp_doc])
            
        except Exception as e:
            # Fallback if pdfplumber fails
            print(f"Error parsing PDF with pdfplumber: {e}")
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
