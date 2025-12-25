from typing import List, Sequence
from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import BaseNode, Document, TextNode
from llama_index.core.node_parser import SentenceSplitter

class NSEEarningsParser(NodeParser):
    """
    Parser specialized for NSE Earnings Reports and Transcripts.
    Phase 1: Wrapper around SentenceSplitter (Passthrough)
    Phase 2: Will implement specific logic for Tables (PDFPlumber) and Dialogues.
    """
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 20):
        super().__init__()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Default splitting logic for Phase 1
        self._splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def _parse_nodes(self, nodes: Sequence[BaseNode], show_progress: bool = False, **kwargs) -> List[BaseNode]:
        """
        Required implementation for NodeParser. 
        Takes list of documents/nodes and returning split nodes.
        """
        # For Phase 1, just delegate to standard splitter
        return self._splitter.get_nodes_from_documents(nodes, show_progress=show_progress)

    def get_nodes_from_documents(self, documents: Sequence[Document], show_progress: bool = False, **kwargs) -> List[BaseNode]:
        """
        Main entry point
        """
        return self._parse_nodes(documents, show_progress=show_progress, **kwargs)
