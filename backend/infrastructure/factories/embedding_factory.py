import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding

class EmbeddingFactory:
    @staticmethod
    def get_embedding_model() -> "BaseEmbedding":
        """
        Returns a configured LlamaIndex Embedding model instance.
        Default: OpenAI (text-embedding-3-small)
        """
        provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        if provider == "openai":
            from llama_index.embeddings.openai import OpenAIEmbedding
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            return OpenAIEmbedding(model=model_name, api_key=api_key)

        elif provider == "ollama":
            from llama_index.embeddings.ollama import OllamaEmbedding
            base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
            # For Docker to talk to host Ollama, use host.docker.internal usually
            return OllamaEmbedding(model_name=model_name, base_url=base_url)
            
        else:
            raise ValueError(f"Unsupported Embedding provider: {provider}")
