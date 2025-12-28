from abc import ABC, abstractmethod
from typing import List, Optional, Any
from pathlib import Path
import logging
import os

from llama_index.core.schema import BaseNode, Document, TextNode
from llama_index.core.node_parser import SentenceSplitter

logger = logging.getLogger(__name__)

class IPdfParsingStrategy(ABC):
    """
    Abstract Base Class for PDF Parsing Strategies.
    """
    @abstractmethod
    def parse(self, doc: Document, splitter: SentenceSplitter) -> List[BaseNode]:
        """
        Parse a PDF document into a list of Nodes (Text/Table).
        """
        pass

class AzureParsingStrategy(IPdfParsingStrategy):
    """
    Concrete implementation using Azure Document Intelligence (Layout Model).
    """
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None):
        self.endpoint = endpoint or os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
        self.key = key or os.getenv("AZURE_FORM_RECOGNIZER_KEY")
        
    def parse(self, doc: Document, splitter: SentenceSplitter) -> List[BaseNode]:
        file_path = doc.metadata.get("file_path")
        if not file_path:
            logger.warning("No file_path found for Azure parser.")
            return []
            
        if not self.endpoint or not self.key:
            logger.error("Azure credentials (endpoint/key) not configured.")
            raise ValueError("Missing Azure Document Intelligence credentials")

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            from azure.ai.documentintelligence.models import DocumentContentFormat
            
            client = DocumentIntelligenceClient(
                endpoint=self.endpoint, 
                credential=AzureKeyCredential(self.key)
            )
            
            with open(file_path, "rb") as f:
                poller = client.begin_analyze_document(
                    "prebuilt-layout", 
                    body=f,
                    content_type="application/pdf",
                    output_content_format=DocumentContentFormat.MARKDOWN
                )
            
            result = poller.result()
            nodes = []
            
            # 1. Text (Markdown)
            # Azure v4.0 returns 'content' as markdown if requested
            if result.content:
                 md_doc = Document(text=result.content, metadata=doc.metadata)
                 text_nodes = splitter.get_nodes_from_documents([md_doc])
                 nodes.extend(text_nodes)
                 logger.info(f"[AzureStrategy] Generated {len(text_nodes)} text nodes from markdown.")

            # 2. Extract Tables
            # We also get structured tables to create explicit TableNodes
            if result.tables:
                logger.info(f"[AzureStrategy] Found {len(result.tables)} tables.")
                for i, table in enumerate(result.tables):
                    # Construct Markdown Table manually or use content if mapped? 
                    # Simpler to reconstruct from cells since we want clean data
                    
                    # Naive reconstruction for Table Node JSON
                    rows = []
                    # We need to determine grid size
                    row_count = table.row_count
                    col_count = table.column_count
                    
                    # Initialize empty grid
                    grid = [["" for _ in range(col_count)] for _ in range(row_count)]
                    
                    for cell in table.cells:
                        r_start = cell.row_index
                        c_start = cell.column_index
                        # Azure SDK usually uses snake_case for attributes
                        row_span = getattr(cell, 'row_span', 1) or 1
                        col_span = getattr(cell, 'column_span', 1) or 1
                        content = cell.content or ""
                        
                        # Fill all cells in the span with the same content (Repeating value strategy)
                        # This ensures every column has context, crucial for LLM understanding.
                        for r in range(r_start, r_start + row_span):
                            for c in range(c_start, c_start + col_span):
                                if r < row_count and c < col_count:
                                    grid[r][c] = content
                        
                    # Assume first row is header? Azure doesn't strictly say always
                    headers = grid[0]
                    data_rows = grid[1:]
                    
                    # Create markdown representation
                    # We can use tabulate or pandas or simple string join
                    # Let's use simple join for now or rely on the text content if it was good.
                    # But explicit TableNode is better.
                    try:
                        import pandas as pd
                        df = pd.DataFrame(data_rows, columns=headers)
                        markdown_table = df.to_markdown(index=False)
                        
                        table_node = TextNode(
                            text=f"Table {i+1}:\n{markdown_table}",
                            metadata={
                                **doc.metadata,
                                "is_table": True,
                                "table_rows": row_count,
                                "table_columns": col_count,
                                "table_json": {
                                    "headers": headers,
                                    "rows": data_rows
                                }
                            }
                        )
                        nodes.append(table_node)
                    except ImportError:
                         # Fallback if pandas missing (it is in requirements?)
                         pass

            return nodes

        except Exception as e:
            logger.error(f"Azure parsing failed: {e}")
            raise

class DoclingParsingStrategy(IPdfParsingStrategy):
    """
    Concrete implementation using Docling.
    Supports configuration for performance (Fast mode, OCR).
    """
    def __init__(self, fast_mode: bool = True, do_ocr: bool = False):
        self.fast_mode = fast_mode
        self.do_ocr = do_ocr

    def parse(self, doc: Document, splitter: SentenceSplitter) -> List[BaseNode]:
        file_path = doc.metadata.get("file_path")
        if not file_path:
            logger.warning("No file_path found in document metadata for Docling.")
            return []

        try:
            # Lazy import to keep dependencies optional/local
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
            
            logger.info(f"[DoclingStrategy] Starting conversion for: {Path(file_path).name} (Fast={self.fast_mode}, OCR={self.do_ocr})")
            
            # Configure Options
            options = PdfPipelineOptions()
            options.do_ocr = self.do_ocr
            options.do_table_structure = True
            options.table_structure_options.do_cell_matching = True
            
            if self.fast_mode:
                options.table_structure_options.mode = TableFormerMode.FAST
            
            # Initialize Converter with options
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=options)
                }
            )
            
            # Convert
            result = converter.convert(file_path)
            doc_obj = result.document
            
            nodes = []
            
            # 1. Extract Text (Markdown)
            full_markdown = doc_obj.export_to_markdown()
            if full_markdown.strip():
                md_doc = Document(text=full_markdown, metadata=doc.metadata)
                text_nodes = splitter.get_nodes_from_documents([md_doc])
                nodes.extend(text_nodes)
                logger.info(f"[DoclingStrategy] Generated {len(text_nodes)} text nodes.")
                
            # 2. Extract Tables
            if doc_obj.tables:
                logger.info(f"[DoclingStrategy] Found {len(doc_obj.tables)} tables.")
                for i, table in enumerate(doc_obj.tables):
                    try:
                        df = table.export_to_dataframe()
                        if df.empty: continue
                        
                        headers = [str(h) for h in df.columns.tolist()]
                        rows = [[str(c) for c in r] for r in df.values.tolist()]
                        
                        markdown_table = df.to_markdown(index=False)
                        
                        table_node = TextNode(
                            text=f"Table {i+1}:\n{markdown_table}",
                            metadata={
                                **doc.metadata,
                                "is_table": True,
                                "table_rows": len(rows),
                                "table_columns": len(headers),
                                "table_json": {"headers": headers, "rows": rows}
                            }
                        )
                        nodes.append(table_node)
                    except Exception as te:
                        logger.warning(f"[DoclingStrategy] Table {i} processing failed: {te}")
                        
            return nodes

        except ImportError:
            logger.error("Docling not installed.")
            raise
        except Exception as e:
            logger.error(f"Docling parsing execution failed: {e}")
            raise
