import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.llms import LLM

class LLMFactory:
    @staticmethod
    def get_llm() -> "LLM":
        """
        Returns a configured LlamaIndex LLM instance based on environment configuration.
        Default: OpenAI
        """
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        model = os.getenv("LLM_MODEL", "gpt-5-nano")
        
        if provider == "mock":
            from llama_index.core.llms import MockLLM
            return MockLLM()

        elif provider == "openai":
            from llama_index.llms.openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            return OpenAI(model=model, api_key=api_key)
            
        # elif provider == "vertex":
        #     return Vertex(model=model, project=settings.google_project_id)
            
        elif provider == "ollama":
            from llama_index.llms.ollama import Ollama
            base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
            return Ollama(model=model, base_url=base_url, request_timeout=300.0)
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
