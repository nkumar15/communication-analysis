import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding

class EmbeddingFactory:
    @staticmethod
    def get_embedding_model() -> "BaseEmbedding":
        """
        Returns a configured LlamaIndex Embedding model instance.
        Default: HuggingFace (BAAI/bge-small-en-v1.5)
        """
        provider = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        
        if provider == "huggingface":
            # Runs locally/in-container
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            return HuggingFaceEmbedding(model_name=model_name)
            
        elif provider == "openai":
            from llama_index.embeddings.openai import OpenAIEmbedding
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            return OpenAIEmbedding(model=model_name, api_key=api_key)
            
        # elif provider == "vertex":
        #     return VertexTextEmbedding(model_name=model_name, project=os.getenv("GOOGLE_PROJECT_ID"))
            
        else:
            raise ValueError(f"Unsupported Embedding provider: {provider}")
