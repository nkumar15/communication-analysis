import os
import json
import asyncio
import sys
from pathlib import Path
from typing import List, Dict

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) 
sys.path.append("/app") 

# Direct Component Imports
try:
    from infrastructure.factories.embedding_factory import EmbeddingFactory
    from modules.domains.b2c.finance_trader.services.retrievers.hybrid_retriever import TenantAwareHybridRetriever
    from llama_index.core import Settings
    from sentence_transformers import CrossEncoder
except ImportError as e:
    print(f"Import Error: {e}")
    from backend.infrastructure.factories.embedding_factory import EmbeddingFactory
    from backend.modules.domains.b2c.finance_trader.services.retrievers.hybrid_retriever import TenantAwareHybridRetriever
    from llama_index.core import Settings
    from sentence_transformers import CrossEncoder

    from sentence_transformers import CrossEncoder

# Import DeepEval
from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualRecallMetric
from deepeval.test_case import LLMTestCase
from deepeval.models import DeepEvalBaseLLM

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATASET_FILE = SCRIPT_DIR / "data/dataset/gold_dataset.json"
INDEX_NAME = "rag_documents_exp1"
TENANT_ID = "05b51fa4-45f4-50c2-b3f4-4c122000347b"

class GPT5Nano(DeepEvalBaseLLM):
    def __init__(self):
        self.model_name = "gpt-5-nano"

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0
        )
        return response.choices[0].message.content

    async def a_generate(self, prompt: str) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0
        )
        return response.choices[0].message.content
        
    def get_model_name(self):
        return self.model_name

async def run_experiment_3_evaluation():
    print("--- Starting Experiment 3 Evaluation (Hybrid + Reranking) ---")
    
    # 1. Load Data
    if not DATASET_FILE.exists():
        print(f"Error: Dataset {DATASET_FILE} not found.")
        return
    with open(DATASET_FILE, "r") as f:
        gold_data = json.load(f)[:3] # Subsample
        
    # 2. Initialize Components
    print("Initializing Hybrid Retriever + Reranker (CrossEncoder)...")
    embed_model = EmbeddingFactory.get_embedding_model()
    Settings.embed_model = embed_model
    
    # Hybrid (Recall Stage)
    retriever = TenantAwareHybridRetriever(
        embed_model=embed_model,
        tenant_id=TENANT_ID,
        top_k=20, # Fetch candidates
        index_name=INDEX_NAME
    )
    
    # Reranker (Precision Stage)
    # Using ms-marco-MiniLM-L-6-v2 directly
    cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    TOP_N_RERANK = 5
    
    test_cases = []
    
    # 3. Predict
    for item in gold_data:
        query = item["input"]
        expected_output = item["expected_output"]
        
        print(f"Querying: {query}")
        
        try:
            # A. Retrieve
            nodes = await retriever.aretrieve(query)
            
            if not nodes:
                print("No nodes retrieved.")
                continue

            # B. Rerank
            # Prepare pairs for CrossEncoder: [[query, doc_text], ...]
            node_texts = [n.node.text for n in nodes]
            pairs = [[query, text] for text in node_texts]
            
            # Predict scores
            scores = cross_encoder.predict(pairs)
            
            # Attach scores to nodes and sort
            for i, node in enumerate(nodes):
                node.score = float(scores[i])
                
            # Sort by new Cross-Encoder score
            nodes.sort(key=lambda x: x.score, reverse=True)
            
            # Top-N
            final_nodes = nodes[:TOP_N_RERANK]
            
            # C. Generate
            from llama_index.llms.openai import OpenAI
            llm = OpenAI(model="gpt-4", temperature=1.0) 
            llm.model = "gpt-5-nano" 
            
            context_str = "\n\n".join([n.text for n in final_nodes])
            prompt = f"Context:\n{context_str}\n\nQuestion: {query}\nAnswer:"
            response = llm.complete(prompt)
            actual_output = response.text
            
            test_case = LLMTestCase(
                input=query,
                actual_output=actual_output,
                expected_output=expected_output,
                retrieval_context=[n.text for n in final_nodes],
                context=item.get("context", [])
            )
            test_cases.append(test_case)
            
        except Exception as e:
            print(f"Error on {query}: {e}")
            import traceback
            traceback.print_exc()
            
    # 4. Evaluate
    if not test_cases:
        return
        
    print(f"Running DeepEval on {len(test_cases)} cases...")
    eval_llm = GPT5Nano()
    results = evaluate(
        test_cases=test_cases,
        metrics=[
            FaithfulnessMetric(threshold=0.5, model=eval_llm),
            AnswerRelevancyMetric(threshold=0.5, model=eval_llm),
            ContextualRecallMetric(threshold=0.5, model=eval_llm)
        ]
    )
    print("\n--- Results ---")
    print(results)

if __name__ == "__main__":
    asyncio.run(run_experiment_3_evaluation())
