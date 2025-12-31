import os
import json
import asyncio
import sys
from pathlib import Path
from typing import List, Dict
from uuid import UUID

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))) 
sys.path.append("/app") 

try:
    from modules.domains.nse.services.rag_service import RagService
    from llama_index.core import Settings
    from llama_index.llms.openai import OpenAI
except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback usually not needed inside Docker
    sys.exit(1)

# Import DeepEval
from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualRecallMetric
from deepeval.test_case import LLMTestCase

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATASET_PATH = SCRIPT_DIR.parent.parent.parent / "evaluation/datasets/nse/golden_datasets/unified_gold_dataset.json"
LOG_FILE = SCRIPT_DIR.parent.parent.parent / "evaluation/projects/nse/data/experiment_logs.json"

# Tenant ID (TCS Test Tenant)
TENANT_ID = UUID("05b51fa4-45f4-50c2-b3f4-4c122000347b")

async def run_integration_evaluation():
    print("--- Starting Integration RAG Evaluation (via RagService) ---")
    
    # 1. Initialize Settings & RagService
    try:
        from infrastructure.factories.embedding_factory import EmbeddingFactory
        Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.0)
        Settings.embed_model = EmbeddingFactory.get_embedding_model()
        
        rag_service = RagService()
        print("RagService initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize RagService/Settings: {e}")
        return

    # 2. Load Unified Dataset
    if not DATASET_PATH.exists():
        print(f"Error: Dataset {DATASET_PATH} not found.")
        # Fallback to absolute path check?
        # The path construction might be relative to CWD options
        print(f"Resolved path: {DATASET_PATH.resolve()}")
        return
        
    with open(DATASET_PATH, "r") as f:
        gold_data = json.load(f)
    print(f"Loaded {len(gold_data)} test cases.")

    # 3. Setup Generator (for Synthesis)
    # RagService.search() retrieves nodes, but we need to generate the "actual_output"
    # using the retrieved context to measure Faithfulness properly.
    llm = OpenAI(model="gpt-4o-mini", temperature=0.0)
    
    test_cases = []
    
    print("\n--- Phase 1: Retrieval & Synthesis ---")
    
    for i, item in enumerate(gold_data):
        query = item["input"]
        expected_output = item["expected_output"]
        
        print(f"[{i+1}/{len(gold_data)}] Querying: {query}")
        
        try:
            # A. Retrieve via RagService (Decompose -> Hybrid Search -> Rerank)
            # This implicitly tests our new "Report Type" filtering logic
            result = await rag_service.search(query, TENANT_ID, limit=8)
            
            # Extract Filters found (debug)
            filters = result.get("filters", [])
            print(f"   > Auto-Filters: {filters}")
            
            # Extract Context
            nodes = result["results"]
            retrieval_context = [n["text"] for n in nodes]
            metadata_list = [n["metadata"] for n in nodes]

            # B. Synthesize Answer
            context_str = "\n\n".join(retrieval_context)
            
            prompt = (
                "You are a strict financial analyst. Follow these steps:\n"
                "1. Read the provided Context carefully.\n"
                "2. Extract exact quotes from the Context that answer the Question.\n"
                "3. If no relevant quotes are found, say 'I don't know'.\n"
                "4. Write your final Answer based ONLY on the extracted quotes.\n\n"
                f"Context:\n{context_str}\n\n"
                f"Question: {query}\n"
                "Answer:"
            )
            
            response = await llm.acomplete(prompt)
            actual_output = response.text
            
            print(f"   > Answer Preview: {actual_output[:100]}...")
            
            # C. Create Test Case
            test_case = LLMTestCase(
                input=query,
                actual_output=actual_output,
                expected_output=expected_output,
                retrieval_context=retrieval_context,
                context=item.get("context", []) # Expected context from Goldenset? (Often empty if generated from scratch)
            )
            test_cases.append(test_case)
            
        except Exception as e:
            print(f"   > Error processing query: {e}")
            import traceback; traceback.print_exc()

    # 4. Evaluate Metrics
    if not test_cases:
        print("No test cases to evaluate.")
        return

    print("\n--- Phase 2: DeepEval Metrics ---")
    
    # Define Metrics
    faithfulness = FaithfulnessMetric(threshold=0.5, model="gpt-4o-mini") 
    answer_relevancy = AnswerRelevancyMetric(threshold=0.5, model="gpt-4o-mini")
    contextual_recall = ContextualRecallMetric(threshold=0.5, model="gpt-4o-mini")
    
    test_results = []
    
    # Run sequentially (Rate Limit protection)
    for i, tc in enumerate(test_cases):
        print(f"Evaluating Case {i+1}...")
        try:
            er = evaluate(test_cases=[tc], metrics=[faithfulness, answer_relevancy, contextual_recall], print_results=False)
            test_results.extend(er.test_results)
            await asyncio.sleep(2) # Politeness delay
        except Exception as e:
            print(f"Metric evaluation failed for case {i+1}: {e}")

    # 5. Summarize & Log
    # Calculate averages
    scores = {"faithfulness": [], "answer_relevancy": [], "contextual_recall": []}
    
    for res in test_results:
        for m in res.metrics_data:
            key = m.name.lower().replace(" ", "_")
            if key in scores:
                scores[key].append(m.score)
                
    avgs = {k: (sum(v)/len(v) if v else 0) for k, v in scores.items()}
    
    print("\n--- Results Summary ---")
    print(json.dumps(avgs, indent=2))
    
    # Save Log
    log_entry = {
         "timestamp": "2025-12-31T23:59:59", # Approximation, use standard lib in prod
         "metrics": avgs,
         "details": f"Integration Test with RagService (ReportType Support: Yes). Cases: {len(test_cases)}"
    }
    
    # Ensure dir exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        else:
            logs = []
        logs.append(log_entry)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)
        print(f"Logged to {LOG_FILE}")
    except Exception as e:
       print(f"Logging failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_integration_evaluation())
