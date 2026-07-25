from functools import lru_cache
from typing import Optional, Any
import os

class RerankerFactory:
    _model_instance = None
    
    @classmethod
    def get_reranker(cls, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> Any:
        """
        Get or initialize the CrossEncoder model.
        Uses a singleton pattern (or class-level cache) to avoid reloading the model.
        """
        if cls._model_instance is None:
            try:
                from sentence_transformers import CrossEncoder
                # Initialize the model
                # We can use the huggingface cache dir if set in env
                cache_folder = os.getenv("HF_HOME")
                cls._model_instance = CrossEncoder(model_name)
                print(f"Reranker model '{model_name}' loaded successfully.")
            except ImportError:
                print("sentence-transformers not installed. Reranking will not be available.")
                return None
            except Exception as e:
                print(f"Failed to load reranker model '{model_name}': {e}")
                return None
                
        return cls._model_instance

    @classmethod
    def predict(cls, query: str, documents: list[str], top_k: int = 10) -> list[tuple[int, float]]:
        """
        Rerank a list of documents against a query.
        Returns a list of (index, score) tuples, sorted by score descending.
        """
        model = cls.get_reranker()
        if not model:
            # Fallback: return original indices with dummy scores if model fails
            return [(i, 0.0) for i in range(len(documents))][:top_k]
            
        pairs = [[query, doc] for doc in documents]
        try:
            # Check if model output requires sigmoid (CrossEncoder default for some models is logits)
            # ms-marco-MiniLM-L-6-v2 returns logits.
            import numpy as np
            scores = model.predict(pairs)
            
            # Apply Sigmoid: 1 / (1 + exp(-x))
            scores = 1 / (1 + np.exp(-scores))
            
            # Create list of (original_index, score)
            results = list(enumerate(scores))
            # Sort by score desc
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        except Exception as e:
            print(f"Prediction failed: {e}")
            return [(i, 0.0) for i in range(len(documents))][:top_k]
