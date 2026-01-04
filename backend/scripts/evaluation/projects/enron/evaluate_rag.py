import os
import json
import asyncio
import sys
import argparse
import yaml
from pathlib import Path
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

# Add root to sys.path
# If running inside container /app is root
if os.path.exists("/app"):
    sys.path.append("/app")
else:
    # Host fallback
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

try:
    from modules.domains.enron.services.rag import enron_rag_service
    from modules.domains.enron.constants import DEFAULT_TENANT_ID
    from llama_index.core import Settings
    from llama_index.llms.openai import OpenAI
    from infrastructure.factories.embedding_factory import EmbeddingFactory
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Import DeepEval
try:
    from deepeval import evaluate
    from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualRecallMetric
    from deepeval.test_case import LLMTestCase
except ImportError:
    print("DeepEval not installed. Please install deepeval.")
    sys.exit(1)

async def run_evaluation(config_path: str):
    print(f"🚀 Starting Enron RAG Evaluation with config: {config_path}")
    
    # 1. Load Config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    dataset_path = Path(config["dataset_path"])
    # Resolve relative paths relative to /app if in container
    if not dataset_path.exists() and os.path.exists("/app"):
        dataset_path = Path("/app") / config["dataset_path"]
        
    output_dir = Path(config["output_dir"])
    if not output_dir.exists() and os.path.exists("/app"):
        output_dir = Path("/app") / config["output_dir"]
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Initialize Service
    try:
        Settings.llm = OpenAI(model=config["pipeline"]["llm"]["model"], temperature=config["pipeline"]["llm"]["temperature"])
        Settings.embed_model = EmbeddingFactory.get_embedding_model()
        enron_rag_service._ensure_initialized()
        print("✅ RagService initialized.")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # 3. Load Dataset
    if not dataset_path.exists():
        print(f"❌ Dataset {dataset_path} not found.")
        return
        
    with open(dataset_path, "r") as f:
        gold_data = json.load(f)
    print(f"Loaded {len(gold_data)} test cases.")

    # 4. Prepare Test Cases (Retrieval + Synthesis)
    llm = OpenAI(model="gpt-4o-mini", temperature=0.0)
    test_cases = []
    
    print("\n--- Phase 1: Retrieval & Synthesis ---")
    
    # Handle both new 'unified' format (list of dicts) and old 'golden_set' format
    # user's golden_set.json has: [{query, expected_keywords}] OR [{input, expected_output}]?
    # My created golden_set.json (Step 2307) had: {query, expected_keywords, ...}
    # DeepEval expects 'expected_output'. Keyword match is weak. 
    # For now, I'll use keywords as 'expected_output' or just rely on ContextualRecall which checks context vs expected.
    # Actually, DeepEval needs `expected_output` text for AnswerRelevancy/Faithfulness? No, Faithfulness checks Actual vs Context. Relevancy checks Actual vs Input.
    # ContextualRecall checks Context vs Expected Output. 
    # Since I only have keywords, ContextualRecall might be weak if I just pass string of keywords.
    # But let's try.
    
    for i, item in enumerate(gold_data):
        query = item.get("query") or item.get("input")
        expected_keywords = item.get("expected_keywords", [])
        expected_output = item.get("expected_output", ", ".join(expected_keywords))
        
        print(f"[{i+1}/{len(gold_data)}] Querying: {query}")
        
        try:
            # Search
            # limit from config
            limit = config["pipeline"]["retriever"].get("top_k", 10)
            result = await enron_rag_service.search(query=query, tenant_id=DEFAULT_TENANT_ID, limit=limit)
            
            # Format results
            nodes = result.get("results", []) # list of dicts {text, score, ...}
            retrieval_context = [n["text"] for n in nodes]
            
            # Synthesize Answer (RAG)
            context_str = "\n\n".join(retrieval_context)
            prompt = (
                "You are an Enron investigation analyst.\n"
                "Answer the question based ONLY on the provided Context.\n"
                f"Context:\n{context_str}\n\n"
                f"Question: {query}\n"
                "Answer:"
            )
            response = await llm.acomplete(prompt)
            actual_output = response.text
            
            tc = LLMTestCase(
                input=query,
                actual_output=actual_output,
                expected_output=expected_output,
                retrieval_context=retrieval_context
            )
            test_cases.append(tc)
            
        except Exception as e:
            print(f"Error processing {query}: {e}")

    # 5. Evaluate (with Throttling)
    print("\n--- Phase 2: DeepEval Metrics ---")
    
    metrics = [
        FaithfulnessMetric(threshold=0.5, model="gpt-4o-mini"),
        AnswerRelevancyMetric(threshold=0.5, model="gpt-4o-mini"),
        ContextualRecallMetric(threshold=0.5, model="gpt-4o-mini")
    ]
    
    test_results = []
    
    for i, tc in enumerate(test_cases):
        print(f"Evaluating Case {i+1}...")
        try:
            er = evaluate(test_cases=[tc], metrics=metrics)
            test_results.extend(er.test_results)
            # Throttling to avoid rate limits
            await asyncio.sleep(2) 
        except Exception as e:
            print(f"Metric evaluation failed for case {i+1}: {e}")

    # 6. Summarize
    scores = {"faithfulness": [], "answer_relevancy": [], "contextual_recall": []}
    for res in test_results:
        for m in res.metrics_data:
            key = m.name.lower().replace(" ", "_")
            if key in scores:
                scores[key].append(m.score)
                
    avgs = {k: (sum(v)/len(v) if v else 0) for k, v in scores.items()}
    
    print("\n--- Results Summary ---")
    print(json.dumps(avgs, indent=2))
    
    # 7. Save Results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_name = config.get("name", "experiment")
    filename = f"experiment_{exp_name}_{timestamp}.json"
    filepath = output_dir / filename
    
    result_data = {
        "config": config,
        "metrics": avgs,
        "details": [
            {
                "input": res.input,
                "actual_output": res.actual_output,
                "metrics": {m.name: m.score for m in res.metrics_data}
            }
            for res in test_results
        ]
    }
    
    with open(filepath, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"✅ Results saved to {filepath}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to experiment config yaml")
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(args.config))
