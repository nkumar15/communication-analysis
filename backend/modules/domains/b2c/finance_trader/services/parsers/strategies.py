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
            import hashlib
            import json
            from azure.ai.documentintelligence.models import AnalyzeResult
            
            # 0. Setup Cache
            # Use content hash to be robust against file renames
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            content_hash = hashlib.sha256(file_bytes).hexdigest()
            
            cache_dir = Path(os.getenv("AZURE_CACHE_DIR", ".cache/azure_results"))
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{content_hash}.json"
            
            result_dict = None
            result = None
            
            # 1. Check Cache
            if cache_file.exists():
                logger.info(f"[AzureStrategy] Cache Hit: {cache_file}")
                with open(cache_file, "r") as f:
                    result_dict = json.load(f)
                # Rehydrate SDK object from dict
                result = AnalyzeResult(result_dict)
            else:
                # 2. Call Azure (Cache Miss)
                logger.info(f"[AzureStrategy] Cache Miss. Calling Azure API...")
                from azure.ai.documentintelligence import DocumentIntelligenceClient
                from azure.core.credentials import AzureKeyCredential
                from azure.ai.documentintelligence.models import DocumentContentFormat, AnalyzeOutputOption, DocumentAnalysisFeature
                
                client = DocumentIntelligenceClient(
                    endpoint=self.endpoint, 
                    credential=AzureKeyCredential(self.key)
                )
                
                # Rewind file for API call
                import io
                f_stream = io.BytesIO(file_bytes)
                
                # Future-Proofing: Enable Styling and Figures extraction now 
                # to avoid re-parsing later. (Parse Once, Cache Forever)
                poller = client.begin_analyze_document(
                    "prebuilt-layout", 
                    body=f_stream,
                    content_type="application/pdf",
                    output_content_format=DocumentContentFormat.MARKDOWN,
                    output=[AnalyzeOutputOption.FIGURES],
                    features=[DocumentAnalysisFeature.STYLE_FONT]
                )
                
                result = poller.result()
                
                # 3. Save to Cache
                # SDK objects have .as_dict() which is standard for serialization
                if hasattr(result, "as_dict"):
                    result_dict = result.as_dict()
                    
                    # FORCE EXPLICIT TABLE SERIALIZATION & DEBUGGING
                    table_count = len(result.tables) if result.tables else 0
                    figure_count = len(result.figures) if result.figures else 0
                    page_count = len(result.pages) if result.pages else 0
                    
                    logger.info(f"Azure API Response Stats: Pages={page_count}, Tables={table_count}, Figures={figure_count}")
                    print(f"DEBUGGING ADI: Found {table_count} tables, {figure_count} figures, {page_count} pages.")

                    # FORCE EXPLICIT SERIALIZATION FOR ALL COMPONENTS
                    # The default .as_dict() seems to be shallow or missing fields in some SDK versions
                    
                    # 1. Tables
                    if result.tables:
                        print(f"DEBUGGING ADI: Explicitly listing {table_count} tables.")
                        result_dict['tables'] = [t.as_dict() if hasattr(t, "as_dict") else t for t in result.tables]
                    
                    # 2. Paragraphs (Crucial for text)
                    if result.paragraphs:
                        paragraph_count = len(result.paragraphs)
                        print(f"DEBUGGING ADI: Explicitly listing {paragraph_count} paragraphs.")
                        result_dict['paragraphs'] = [p.as_dict() if hasattr(p, "as_dict") else p for p in result.paragraphs]

                    # 3. Pages (Crucial for OCR/Lines)
                    if result.pages:
                        print(f"DEBUGGING ADI: Explicitly listing {page_count} pages.")
                        result_dict['pages'] = [p.as_dict() if hasattr(p, "as_dict") else p for p in result.pages]
                        
                    # 4. Styles (Crucial for handwritten/font logic)
                    if result.styles:
                        style_count = len(result.styles)
                        print(f"DEBUGGING ADI: Explicitly listing {style_count} styles.")
                        result_dict['styles'] = [s.as_dict() if hasattr(s, "as_dict") else s for s in result.styles]

                    with open(cache_file, "w") as f:
                        json.dump(result_dict, f, default=str)
                        logger.info(f"[AzureStrategy] Cached result to {cache_file} (Size: {f.tell()} bytes)")
                    print(f"DEBUGGING ADI: Successfully wrote cache file at {cache_file}")
                else:
                    logger.warning("[AzureStrategy] Could not serialize result (no as_dict). Cache skipped.")

            if not result:
                raise ValueError("Failed to obtain AnalyzeResult from Cache or API")
                
            # 2a. Stage 2: Metadata Enrichment (One-Pass)
            # Parse Once, Enrich Offline. Use cached content for metadata extraction.
            enriched_metadata = doc.metadata.copy()
            try:
                # Lazy import to avoid circular dependency or heavy init if unused
                from .metadata import MetadataExtractor
                extractor = MetadataExtractor() # Default gpt-4o-mini
                
                # Use first 4000 chars (approx first 1-2 pages) for context
                context_text = ""
                if result.content:
                    context_text = result.content[:4000]
                
                if context_text:
                    logger.info("[AzureStrategy] Extracting Metadata from cached text...")
                    meta_obj = extractor.extract(context_text)
                    
                    if meta_obj.ticker: enriched_metadata["ticker"] = meta_obj.ticker
                    if meta_obj.company_name: enriched_metadata["company_name"] = meta_obj.company_name
                    if meta_obj.fiscal_year: enriched_metadata["fiscal_year"] = meta_obj.fiscal_year
                    if meta_obj.quarter: enriched_metadata["quarter"] = meta_obj.quarter
                    if meta_obj.scope: enriched_metadata["scope"] = [s.value for s in meta_obj.scope]
                    
                    logger.info(f"[AzureStrategy] Enriched Metadata: {meta_obj.dict(exclude_none=True)}")
            except Exception as e:
                logger.warning(f"[AzureStrategy] Metadata extraction failed: {e}")
                # Continue without enrichment

            nodes = []
            
            # Stage 3: Advanced Structure (Layout-Aware Chunking)
            # Use cached Azure structure (paragraphs/roles) instead of flattening to md
            return self._layout_aware_chunking(result, enriched_metadata, splitter)

        except Exception as e:
            logger.error(f"Azure parsing failed: {e}")
            raise

    def _layout_aware_chunking(self, result: Any, metadata: dict, splitter: SentenceSplitter) -> List[BaseNode]:
        """
        Custom chunking logic that respects document structure.
        1. Merges Paragraphs and Tables into a single stream based on offset.
        2. Respects 'Section Headings' as chunk boundaries.
        3. Prepends active Section Title to chunk text.
        """
        try:
            import pandas as pd
            import re

            nodes = []
            
            # 1. Deduplicate & Merge Logic
            # Azure separates content into paragraphs (text) and tables (structured).
            # Often text inside tables is ALSO in paragraphs. We want the Table Node, not the loose paragraphs.
            
            # Collect Tables spans
            table_spans = []
            tables = result.tables or []
            for i, t in enumerate(tables):
                # Calculate table range
                min_offset = float('inf')
                max_offset = 0
                for r in getattr(t, 'bounding_regions', []) or []:
                    # bounding_regions don't have offset/length usually result.tables[i].spans
                    pass
                # Azure py sdk: table.spans is list of spans
                for span in getattr(t, 'spans', []):
                    table_spans.append((span.offset, span.offset + span.length))
                    min_offset = min(min_offset, span.offset)
                    
                # Fallback if spans undefined (older api?), usually present
            
            def is_in_table(offset):
                for start, end in table_spans:
                    if start <= offset < end:
                        return True
                return False

            # Build Element Stream
            elements = []
            
            # Add Tables
            for i, table in enumerate(tables):
                # Get offset for sorting
                spans = getattr(table, 'spans', [])
                offset = spans[0].offset if spans else 0
                
                # Construct DataFrame
                row_count = table.row_count
                col_count = table.column_count
                grid = [["" for _ in range(col_count)] for _ in range(row_count)]
                for cell in table.cells:
                    r_start = cell.row_index
                    c_start = cell.column_index
                    row_span = getattr(cell, 'row_span', 1) or 1
                    col_span = getattr(cell, 'column_span', 1) or 1
                    content = getattr(cell, 'content', "") or ""
                    for r in range(r_start, r_start + row_span):
                        for c in range(c_start, c_start + col_span):
                            if r < row_count and c < col_count:
                                grid[r][c] = content
                
                headers = grid[0]
                data_rows = grid[1:]
                try:
                    df = pd.DataFrame(data_rows, columns=headers)
                    md_table = df.to_markdown(index=False)
                except:
                    md_table = str(grid)

                elements.append({
                    "type": "table",
                    "offset": offset,
                    "content": md_table,
                    "obj": table,
                    "metadata": {
                        "table_rows": row_count, 
                        "table_columns": col_count,
                        "table_json": {"headers": headers, "rows": data_rows}
                    }
                })

            # Add Paragraphs (if not in table)
            paragraphs = result.paragraphs or []
            for p in paragraphs:
                spans = getattr(p, 'spans', [])
                offset = spans[0].offset if spans else 0
                if is_in_table(offset):
                    continue
                
                role = getattr(p, 'role', None) 
                # Use 'content'
                elements.append({
                    "type": "text",
                    "offset": offset,
                    "content": p.content,
                    "role": role, # title, sectionHeading, pageHeader
                    "obj": p
                })

            # Sort by reading order (offset)
            elements.sort(key=lambda x: x["offset"])

            # 2. Chunking Loop
            current_chunk_text = []
            current_metadata = metadata.copy()
            current_section_title = "Introduction" # Default
            
            section_titles_stack = []

            def flush_chunk():
                if not current_chunk_text:
                    return
                
                full_text = "\n\n".join(current_chunk_text)
                
                # Prepend Section Context to text for embedding
                # "Contextual Chunking"
                final_text = f"Section: {current_section_title}\n\n{full_text}"
                
                # Store explicit section in metadata for filtering later
                meta = current_metadata.copy()
                meta["section"] = current_section_title
                
                # Check for Speaker (Regex MVP)
                # If text starts with "Operator:" or "name:", tag it
                # Simple heuristic
                speaker_match = re.match(r'^([A-Z][a-z]+ [A-Z][a-z]+):', full_text[:50])
                if speaker_match:
                    meta["speaker"] = speaker_match.group(1)
                
                node = TextNode(text=final_text, metadata=meta)
                nodes.append(node)
                current_chunk_text.clear()

            for el in elements:
                # Handle Section Changes
                if el["type"] == "text":
                    role = el.get("role")
                    content = el["content"]
                    
                    if role in ["title", "sectionHeading"]:
                        # Boundary detected: Flush previous chunk
                        flush_chunk()
                        # Start new section
                        current_section_title = content
                        # We also add the title to the next chunk's text so it's readable
                        current_chunk_text.append(f"## {content}")
                        continue
                    
                    if role in ["pageHeader", "pageFooter", "pageNumber"]:
                        # Skip noise
                        continue
                    
                    # Normal paragraph
                    current_chunk_text.append(content)
                    
                    # Length check (soft limit) using rough char count or splitter logic
                    # For simplicity, if buffer > 1500 chars, flush (assuming 4 chars/token -> ~400 tokens)
                    if sum(len(s) for s in current_chunk_text) > 1500:
                        flush_chunk()
                        
                elif el["type"] == "table":
                    # Tables forces a flush before and after to keep them as distinct valid nodes
                    flush_chunk()
                    
                    # Create Table Node
                    table_text = f"Section: {current_section_title}\n\n{el['content']}"
                    meta = current_metadata.copy()
                    meta.update(el["metadata"])
                    meta["section"] = current_section_title
                    meta["is_table"] = True
                    
                    node = TextNode(text=table_text, metadata=meta)
                    nodes.append(node)

            # Flush remaining
            flush_chunk()
            
            logger.info(f"[AzureStrategy] Layout-Aware Chunking produced {len(nodes)} nodes (Text+Tables).")
            return nodes

        except Exception as e:
            logger.error(f"Azure parsing failed: {e}")
            raise

class DoclingParsingStrategy(IPdfParsingStrategy):
    """
    Concrete implementation using Docling.
    Optimized for RAG:
    - Uses MarkdownNodeParser for semantic chunking (keeping tables atomic).
    - Removes Base64 images to save tokens.
    - Enables multi-threading for performance.
    """
    def __init__(self, fast_mode: bool = True, do_ocr: bool = True):
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
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions, 
                TableFormerMode
            )
            
            # Acceleration options might be missing in older versions
            try:
                from docling.datamodel.pipeline_options import AccelerationOptions
                HAS_ACCELERATION = True
            except ImportError:
                HAS_ACCELERATION = False
                logger.warning("[DoclingStrategy] AccelerationOptions not available in this docling version.")

            from docling.datamodel.pipeline_options import EasyOcrOptions, TesseractOcrOptions, RapidOcrOptions
            from llama_index.core.node_parser import MarkdownNodeParser
            import re
            
            logger.info(f"[DoclingStrategy] Starting conversion for: {Path(file_path).name}")
            
            # Configure Pipeline Options for Performance
            options = PdfPipelineOptions()
            options.do_ocr = self.do_ocr
            options.do_table_structure = True
            options.table_structure_options.do_cell_matching = True
            
            # Use RapidOCR (Faster than Tesseract/EasyOCR)
            if self.do_ocr:
                try:
                    options.ocr_options = RapidOcrOptions()
                except ImportError:
                    logger.warning("[DoclingStrategy] RapidOCR not found, falling back to default.")

            # Acceleration (Multi-threading)
            if HAS_ACCELERATION:
                try:
                    options.acceleration_options = AccelerationOptions(num_threads=4)
                except TypeError:
                     logger.warning("[DoclingStrategy] AccelerationOptions failed to init.")

            if self.fast_mode:
                options.table_structure_options.mode = TableFormerMode.FAST
            
            # Initialize Converter
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=options)
                }
            )
            
            # Convert
            result = converter.convert(file_path)
            doc_obj = result.document
            
            # Export to Markdown (Standard)
            full_markdown = doc_obj.export_to_markdown()
            
            # Compatibility Fix: Manual Regex Clean for Base64 Images
            # Matches ![...](data:image/...) and replaces with ![Image Placeholder]
            full_markdown = re.sub(r'!\[.*?\]\(data:image\/.*?\)', '', full_markdown)
            
            # Clean Docling internal comments like <!-- image -->
            full_markdown = re.sub(r'<!-- image -->', '', full_markdown)
            
            if not full_markdown.strip():
                logger.warning("[DoclingStrategy] Extracted empty markdown.")
                return []

            # Create a temporary Document for the splitter
            md_doc = Document(text=full_markdown, metadata=doc.metadata)
            
            # Use MarkdownNodeParser instead of SentenceSplitter
            # This respects headers (#, ##) and keeps tables intact.
            md_parser = MarkdownNodeParser()
            nodes = md_parser.get_nodes_from_documents([md_doc])
            
            logger.info(f"[DoclingStrategy] Generated {len(nodes)} nodes using MarkdownNodeParser.")
            return nodes

        except ImportError as ie:
            logger.error(f"Docling import failed: {ie}")
            raise
        except Exception as e:
            logger.error(f"Docling parsing execution failed: {e}")
            raise
