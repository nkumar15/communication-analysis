import os
import json
import asyncio
import sys
from pathlib import Path
from typing import List, Dict

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) 
sys.path.append("/app") 

# Direct Component Imports (Bypassing Service/Router abstraction to test Core Retrieval)
try:
    from infrastructure.factories.embedding_factory import EmbeddingFactory
    from modules.domains.nse.services.retrievers.hybrid_retriever import TenantAwareHybridRetriever
    from llama_index.core import Settings
except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback for local
    from backend.infrastructure.factories.embedding_factory import EmbeddingFactory
    from backend.modules.domains.nse.services.retrievers.hybrid_retriever import TenantAwareHybridRetriever
    from llama_index.core import Settings

# Import DeepEval
from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualRecallMetric
from deepeval.test_case import LLMTestCase

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATASET_FILE = SCRIPT_DIR / "data/dataset/gold_dataset.json"

from deepeval.models import DeepEvalBaseLLM

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

async def run_experiment_1_evaluation():
    print("--- Starting Experiment 1 Evaluation (Advanced Parser) ---")
    
    # 1. Load Golden Dataset
    if not DATASET_FILE.exists():
        print(f"Error: Dataset {DATASET_FILE} not found.")
        return
        
    with open(DATASET_FILE, "r") as f:
        gold_data = json.load(f)
    print(f"Loaded {len(gold_data)} test cases. Subsampling top 3 for rapid baseline.")
    gold_data = gold_data[:3] # baseline speedup
    sys.stdout.flush()

    # 2. Initialize Retriever Components
    print("Initializing Retriever with Index: rag_documents_exp1...")
    sys.stdout.flush()
    embed_model = EmbeddingFactory.get_embedding_model()
    Settings.embed_model = embed_model
    
    # Tenant ID for Experiment 1
    tenant_id = "05b51fa4-45f4-50c2-b3f4-4c122000347b" 
    
    # Initialize Hybrid Retriever with SPECIFIC INDEX
    retriever = TenantAwareHybridRetriever(
        embed_model=embed_model,
        tenant_id=tenant_id,
        top_k=5,
        index_name="rag_documents_exp1"
    )
    
    test_cases = []
    
    # 3. Run Predictions
    for item in gold_data:
        query = item["input"]
        expected_output = item["expected_output"]
        
        print(f"Querying: {query}")
        sys.stdout.flush()
        
        try:
            # Execute Retrieval
            nodes = await retriever.aretrieve(query)
            
            # Synthesize Answer 
            from llama_index.llms.openai import OpenAI
            
            llm = OpenAI(model="gpt-4", temperature=1.0) 
            llm.model = "gpt-5-nano" 
            
            context_str = "\n\n".join([n.text for n in nodes])
            prompt = f"Context:\n{context_str}\n\nQuestion: {query}\nAnswer:"
            response = llm.complete(prompt)
            actual_output = response.text
            
            retrieval_context = [node.text for node in nodes]
            
            test_case = LLMTestCase(
                input=query,
                actual_output=actual_output,
                expected_output=expected_output,
                retrieval_context=retrieval_context,
                context=item.get("context", [])
            )
            test_cases.append(test_case)
            
        except Exception as e:
            print(f"Failed to process query '{query}': {e}")
            import traceback
            traceback.print_exc()

    # 4. Evaluate
    if not test_cases:
        print("No test cases generated. Exiting.")
        return

    print(f"Running DeepEval on {len(test_cases)} cases...")
    
    # Initialize Custom LLM for Metrics
    eval_llm = GPT5Nano()

    # Metrics
    faithfulness = FaithfulnessMetric(threshold=0.5, model=eval_llm) 
    relevancy = AnswerRelevancyMetric(threshold=0.5, model=eval_llm)
    recall = ContextualRecallMetric(threshold=0.5, model=eval_llm)
    
    # Run
    results = evaluate(
        test_cases=test_cases,
        metrics=[faithfulness, relevancy, recall]
    )
    print("\n--- Results ---")
    print(results)

if __name__ == "__main__":
    asyncio.run(run_experiment_1_evaluation())
