from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class RetrieverConfig(BaseModel):
    type: str = Field(..., description="Type of retriever: 'vector', 'hybrid', 'bm25'")
    top_k: int = Field(20, description="Number of candidates to retrieve")
    index_name: Optional[str] = Field(None, description="Detailed index name if needed")
    weights: Optional[List[float]] = Field(None, description="Weights for hybrid search [vector, bm25]")

class RerankerConfig(BaseModel):
    enabled: bool = True
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_n: int = 5

class LLMConfig(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    prompt_strategy: str = "grounding_cot" # grounding_cot, direct

class RAGPipelineConfig(BaseModel):
    retriever: RetrieverConfig
    reranker: Optional[RerankerConfig] = None
    llm: LLMConfig = Field(default_factory=LLMConfig)

class ExperimentConfig(BaseModel):
    name: str
    description: Optional[str] = ""
    pipeline: RAGPipelineConfig
    dataset_path: str
    tenant_id: str
    metrics: List[str] = ["faithfulness", "answer_relevancy", "contextual_recall"]
    output_dir: Optional[str] = None
