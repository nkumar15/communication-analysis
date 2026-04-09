from typing import Any
from llama_index.core import Settings
from llama_index.core.retrievers import BaseRetriever
from tools.genai_evaluator.core.config import RAGPipelineConfig

class RagComponentFactory:
    """
    Factory to create RAG components based on configuration.
    """
    
    @staticmethod
    def create_retriever(config: RAGPipelineConfig, tenant_id: str) -> BaseRetriever:
        """
        Create the retriever component.
        """
        # Load Embedding Model (Global)
        # TODO: Configurable embedding model
        try:
            from infrastructure.factories.embedding_factory import EmbeddingFactory
            embed_model = EmbeddingFactory.get_embedding_model()
            Settings.embed_model = embed_model
        except ImportError:
            # Fallback for local dev without full path setup
            from backend.infrastructure.factories.embedding_factory import EmbeddingFactory
            embed_model = EmbeddingFactory.get_embedding_model()
            Settings.embed_model = embed_model

        if config.retriever.type == "hybrid":
            from tools.genai_evaluator.core.retrievers import TenantAwareHybridRetriever
            
            return TenantAwareHybridRetriever(
                embed_model=embed_model,
                tenant_id=tenant_id,
                top_k=config.retriever.top_k,
                index_name=config.retriever.index_name or "nse_rag_documents"
            )
        
        elif config.retriever.type == "vector":
             # Implementation for standard vector retriever
             # You would load VectorStoreIndex here
             raise NotImplementedError("Vector retriever not yet implemented in factory")
        
        else:
            raise ValueError(f"Unknown retriever type: {config.retriever.type}")

    @staticmethod
    def create_reranker(config: RAGPipelineConfig):
        """
        Create Reranker if enabled.
        """
        if not config.reranker or not config.reranker.enabled:
            return None
            
        from sentence_transformers import CrossEncoder
        return CrossEncoder(config.reranker.model)

    @staticmethod
    def create_llm(config: RAGPipelineConfig):
        """
        Create LLM for synthesis/eval.
        """
        from llama_index.llms.openai import OpenAI
        return OpenAI(
            model=config.llm.model,
            temperature=config.llm.temperature
        )
