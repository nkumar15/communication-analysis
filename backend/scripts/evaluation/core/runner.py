import os
import sys
import json
import yaml
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(ROOT_DIR))

from scripts.evaluation.core.config import ExperimentConfig
from scripts.evaluation.core.factory import RagComponentFactory

# DeepEval imports
from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualRecallMetric
from deepeval.test_case import LLMTestCase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExperimentRunner:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.factory = RagComponentFactory()

    def _load_config(self) -> ExperimentConfig:
        """Load YAML config into Pydantic model"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file {self.config_path} not found")
            
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Validate against model
        return ExperimentConfig(**data)

    def _load_dataset(self) -> List[dict]:
        """Load dataset from path defined in config"""
        # Resolve path relative to backend root or absolute
        data_path = Path(self.config.dataset_path)
        if not data_path.is_absolute():
             data_path = ROOT_DIR / self.config.dataset_path
             
        if not data_path.exists():
            # Try relative to config file for convenience
            data_path = self.config_path.parent / self.config.dataset_path
            
        if not data_path.exists():
             raise FileNotFoundError(f"Dataset {data_path} not found")

        with open(data_path, 'r') as f:
            return json.load(f)

    async def run(self):
        logger.info(f"--- Starting Experiment: {self.config.name} ---")
        dataset = self._load_dataset()
        logger.info(f"Loaded {len(dataset)} test cases.")

        # Initialize Components
        retriever = self.factory.create_retriever(self.config.pipeline, self.config.tenant_id)
        reranker_model = self.factory.create_reranker(self.config.pipeline)
        llm = self.factory.create_llm(self.config.pipeline)
        
        test_cases = []

        # Execution Loop
        for i, item in enumerate(dataset):
            query = item["input"]
            expected_output = item["expected_output"]
            
            logger.info(f"Processing {i+1}/{len(dataset)}: {query}")
            
            try:
                # 1. Retrieve
                nodes = await retriever.aretrieve(query)
                
                # 2. Rerank
                if reranker_model:
                     node_texts = [n.node.text for n in nodes]
                     if node_texts:
                        pairs = [[query, text] for text in node_texts]
                        scores = reranker_model.predict(pairs)
                        
                        for idx, node in enumerate(nodes):
                            node.score = float(scores[idx])
                        
                        nodes.sort(key=lambda x: x.score, reverse=True)
                        nodes = nodes[:self.config.pipeline.reranker.top_n]
                
                # 3. Synthesize
                context_str = "\n\n".join([n.text for n in nodes])
                
                # Simple prompt strategy (can be extracted to factory)
                prompt = (
                    "You are a strict financial analyst.\n"
                    f"Context:\n{context_str}\n\n"
                    f"Question: {query}\n"
                    "Answer:"
                )
                
                response = llm.complete(prompt)
                actual_output = response.text
                
                # 4. Create TestCase
                test_case = LLMTestCase(
                    input=query,
                    actual_output=actual_output,
                    expected_output=expected_output,
                    retrieval_context=[n.text for n in nodes],
                    context=item.get("context", [])
                )
                test_cases.append(test_case)

            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                import traceback
                traceback.print_exc()

        if not test_cases:
            logger.warning("No test cases generated.")
            return

        # Evaluation
        logger.info("Running DeepEval Metrics...")
        # TODO: Load metric configs dynamically
        # Using default GPT-4o-mini for metrics as per previous script
        from deepeval.models import GPTModel # You might need a custom model wrapper if using specific one
        
        # We'll rely on DeepEval defaults or environment vars for now
        # Or instantiate metrics with specific models if needed
        metrics = []
        if "faithfulness" in self.config.metrics:
            metrics.append(FaithfulnessMetric(threshold=0.5, model="gpt-4o-mini"))
        if "answer_relevancy" in self.config.metrics:
            metrics.append(AnswerRelevancyMetric(threshold=0.5, model="gpt-4o-mini"))
        if "contextual_recall" in self.config.metrics:
            metrics.append(ContextualRecallMetric(threshold=0.5, model="gpt-4o-mini"))

        results = evaluate(test_cases=test_cases, metrics=metrics)
        
        self._log_results(results)

    def _log_results(self, eval_results):
        """Log results to file"""
        output_dir = Path(self.config.output_dir) if self.config.output_dir else self.config_path.parent / "results"
        if not output_dir.is_absolute():
            output_dir = ROOT_DIR / str(output_dir)
            
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.name}_{timestamp}.json"
        
        # Serialize results (simplified)
        log_data = {
            "experiment": self.config.name,
            "timestamp": datetime.now().isoformat(),
            "config": self.config.dict(),
            "metrics": {
                 # Calculate averages
                 # This is a bit complex with DeepEval object structure, 
                 # assuming eval_results has test_results
            }
        }
        
        # Simple extraction
        test_results_data = []
        for res in eval_results.test_results:
             test_results_data.append({
                 "input": res.input,
                 "actual_output": res.actual_output,
                 "success": res.success,
                 "metrics": {m.name: m.score for m in res.metrics_data}
             })
        
        log_data["results"] = test_results_data
        
        # Calculate Aggregates
        for metric_name in ["Faithfulness", "Answer Relevancy", "Contextual Recall"]:
            scores = [
                r["metrics"].get(metric_name, 0) 
                for r in test_results_data 
                if metric_name in r["metrics"]
            ]
            if scores:
                 log_data["metrics"][metric_name] = sum(scores) / len(scores)

        with open(output_dir / filename, 'w') as f:
            json.dump(log_data, f, indent=2)
            
        logger.info(f"Results saved to {output_dir / filename}")
        logger.info("Aggregated Metrics:")
        print(json.dumps(log_data["metrics"], indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG Evaluation")
    parser.add_argument("--config", required=True, help="Path to experiment config YAML")
    args = parser.parse_args()

    asyncio.run(ExperimentRunner(args.config).run())
