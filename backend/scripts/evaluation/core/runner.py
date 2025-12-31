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
    def __init__(self, config_path: str, update_registry: bool = False):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.config.update_registry = update_registry
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
        """Log results to file and update registry"""
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
            "metrics": {}
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
        scores = {}
        for metric_name in ["Faithfulness", "Answer Relevancy", "Contextual Recall"]:
            vals = [
                r["metrics"].get(metric_name, 0) 
                for r in test_results_data 
                if metric_name in r["metrics"]
            ]
            if vals:
                 avg = sum(vals) / len(vals)
                 log_data["metrics"][metric_name] = avg
                 scores[metric_name] = avg

        with open(output_dir / filename, 'w') as f:
            json.dump(log_data, f, indent=2)
            
        logger.info(f"Results saved to {output_dir / filename}")
        
        # Update Markdown Registry (only if requested)
        if self.config.update_registry:
            try:
                self._update_registry(scores, output_dir / filename)
            except Exception as e:
                logger.error(f"Failed to update registry: {e}")

    def _update_registry(self, scores: dict, log_file: Path):
        """Update EXPERIMENT_REGISTRY.md"""
        registry_path = self.config_path.parent / "EXPERIMENT_REGISTRY.md"
        if not registry_path.exists():
            logger.warning(f"Registry not found at {registry_path}, skipping update.")
            return

        # Format Metrics
        f_score = f"{scores.get('Faithfulness', 0)*100:.1f}%"
        r_score = f"{scores.get('Answer Relevancy', 0)*100:.1f}%"
        c_score = f"{scores.get('Contextual Recall', 0)*100:.1f}%"
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Determine Exp # (Naively count lines or find last number)
        # We'll just read the file and append
        with open(registry_path, 'r') as f:
            lines = f.readlines()
            
        # Find the last table row to parse the ID
        last_id = "?"
        insert_idx = -1
        
        # Look for the "Dataset v1 (Current - Active)" table or the last table
        # We assume the file ends with the table or notes. 
        # We append to the table before "## Notes" or EOF.
        
        row_format = "| {id} | {name} | {desc} | {f} | {r} | {cr} | {cost} | {date} | ✅ Complete |\n"
        
        # Simple Append Strategy: Find the last line starting with |
        last_table_line_idx = -1
        last_exp_num = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith("|") and "---" not in line and "Exp #" not in line:
                last_table_line_idx = i
                # Try parse number
                try:
                    parts = line.split("|")
                    if len(parts) > 1 and parts[1].strip().isdigit():
                        last_exp_num = int(parts[1].strip())
                except:
                    pass
        
        new_exp_num = last_exp_num + 1
        new_row = row_format.format(
            id=new_exp_num,
            name=self.config.name,
            desc=self.config.description or "N/A",
            f=f_score,
            r=r_score,
            cr=c_score,
            cost="?",
            date=date_str
        )
        
        if last_table_line_idx != -1:
            lines.insert(last_table_line_idx + 1, new_row)
        else:
             # If no table found, append to end
             lines.append("\n" + new_row)

        with open(registry_path, 'w') as f:
            f.writelines(lines)
            
        logger.info(f"Registry updated: Experiment #{new_exp_num}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG Evaluation")
    parser.add_argument("--config", required=True, help="Path to experiment config YAML")
    parser.add_argument("--update-registry", action="store_true", help="Update EXPERIMENT_REGISTRY.md with results")
    args = parser.parse_args()

    asyncio.run(ExperimentRunner(args.config, args.update_registry).run())
