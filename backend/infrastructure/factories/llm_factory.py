import os
from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI
# from llama_index.llms.vertex import Vertex  # Uncomment when Vertex dependency added
# from llama_index.llms.ollama import Ollama # Uncomment when Ollama dependency added
from core.config import settings

class LLMFactory:
    @staticmethod
    def get_llm() -> LLM:
        """
        Returns a configured LlamaIndex LLM instance based on environment configuration.
        Default: OpenAI
        """
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            return OpenAI(model=model, api_key=api_key)
            
        # elif provider == "vertex":
        #     return Vertex(model=model, project=settings.google_project_id)
            
        # elif provider == "ollama":
        #     base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        #     return Ollama(model=model, base_url=base_url)
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
