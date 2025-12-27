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
from pydantic import BaseModel

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATASET_FILE = SCRIPT_DIR / "data/dataset/gold_dataset.json"
LOG_FILE = SCRIPT_DIR / "data/experiment_logs.json"

# Using GPT-4o for evaluation metrics - reliable and proven
# Keep gpt-5-nano for RAG generation (cost-effective)
# Evaluation runs infrequently so GPT-4o cost is acceptable

async def run_baseline_evaluation():
    print("--- Starting Baseline RAG Evaluation (Direct Retriever) ---")
    
    # 1. Load Golden Dataset
    if not DATASET_FILE.exists():
        print(f"Error: Dataset {DATASET_FILE} not found.")
        return
        
    with open(DATASET_FILE, "r") as f:
        gold_data = json.load(f)
    print(f"Loaded {len(gold_data)} test cases. Running FULL evaluation.")
    # gold_data = gold_data[:1]  # Uncomment to test with 1 case
    sys.stdout.flush()

    # 2. Initialize Retriever Components
    print("Initializing Retriever...")
    sys.stdout.flush()
    embed_model = EmbeddingFactory.get_embedding_model()
    Settings.embed_model = embed_model
    
    # Validation Tenant ID (Neeraj's Workspace)
    tenant_id = "05b51fa4-45f4-50c2-b3f4-4c122000347b" 
    
    # Initialize Hybrid Retriever
    # Using top_k=5 to match API default
    retriever = TenantAwareHybridRetriever(
        embed_model=embed_model,
        tenant_id=tenant_id,
        top_k=5
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
            # Using gpt-5-nano as requested. 
            # We initialize with a valid model to pass validation, then override.
            # Explicitly set temperature=1.0 as some reasoning/nano models reject <1.0
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
    
    # Use DeepEval's default model (GPT-4o) for metrics
    # Reliable, proven, worth the cost for evaluation quality

    # Metrics (using default GPT-4o)
    faithfulness = FaithfulnessMetric(threshold=0.5) 
    answer_relevancy = AnswerRelevancyMetric(threshold=0.5)
    contextual_recall = ContextualRecallMetric(threshold=0.5)
    
    
    # Configure rate limiting to avoid hitting OpenAI's 30K TPM limit
    from deepeval.evaluate import AsyncConfig
    
    async_config = AsyncConfig(
        throttle_value=20,  # 20 second delay between test cases to avoid rate limits
        max_concurrent=1   # Max 2 concurrent evaluations
    )
    
    # Run evaluation with rate limit controls
    eval_result = evaluate(
        test_cases=test_cases,
        metrics=[faithfulness, answer_relevancy, contextual_recall],
        async_config=async_config
    )
    
    # Extract test results from EvaluationResult object
    test_results = eval_result.test_results
    print(f"\n--- Evaluation Complete: {len(test_results)} test cases processed ---")
    
    # Calculate average scores
    faithfulness_scores = []
    relevancy_scores = []
    recall_scores = []

    for test_result in test_results:
        for metric_data in test_result.metrics_data:
            metric_name = metric_data.name
            if "Faithfulness" in metric_name:
                faithfulness_scores.append(metric_data.score)
            elif "Answer Relevancy" in metric_name:
                relevancy_scores.append(metric_data.score)
            elif "Contextual Recall" in metric_name:
                recall_scores.append(metric_data.score)

    avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0
    avg_relevancy = sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0
    avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0

    # 5. Log Results
    import datetime
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "config": {
            "eval_model": "gemini-1.5-flash",
            "rag_model": "gpt-5-nano",
            "embedding": "text-embedding-3-small", 
            "top_k": 5,
            "dataset_size": len(test_cases)
        },
        "metrics": {
            "faithfulness": avg_faithfulness,
            "answer_relevancy": avg_relevancy,
            "contextual_recall": avg_recall
        }
    }
    
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        else:
            logs = []
            
        logs.append(log_entry)
        
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)
        print(f"✓ Results logged to {LOG_FILE}")
    except Exception as e:
        print(f"Failed to log results: {e}")

if __name__ == "__main__":
    asyncio.run(run_baseline_evaluation())
