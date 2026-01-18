import os
import sys
import json
import yaml
import asyncio
import argparse
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(ROOT_DIR))

from scripts.evaluation.core.config import ExperimentConfig
from scripts.evaluation.core.factory import RagComponentFactory

# DeepEval imports for generic metrics if needed, but we will calculate classification metrics manually
# from deepeval import evaluate 
# from deepeval.metrics import FaithfulnessMetric 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntentExperimentRunner:
    def __init__(self, config_path: str, update_registry: bool = False):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.config.update_registry = update_registry
        self.factory = RagComponentFactory()

    def _load_config(self) -> ExperimentConfig:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file {self.config_path} not found")
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
        return ExperimentConfig(**data)

    def _load_dataset(self) -> List[dict]:
        data_path = Path(self.config.dataset_path)
        if not data_path.is_absolute():
            # Try 3 locations: 
            # 1. Absolute path based on backend root
            candidate_1 = ROOT_DIR / self.config.dataset_path
            # 2. Relative to config
            candidate_2 = self.config_path.parent / self.config.dataset_path
            # 3. Relative to CWD
            candidate_3 = Path.cwd() / self.config.dataset_path

            if candidate_1.exists():
                data_path = candidate_1
            elif candidate_2.exists():
                data_path = candidate_2
            elif candidate_3.exists():
                data_path = candidate_3
            
        if not data_path.exists():
             raise FileNotFoundError(f"Dataset {self.config.dataset_path} not found")

        with open(data_path, 'r') as f:
            return json.load(f)

    async def run(self):
        logger.info(f"--- Starting Intent Classification Experiment: {self.config.name} ---")
        dataset = self._load_dataset()
        logger.info(f"Loaded {len(dataset)} test cases.")

        llm = self.factory.create_llm(self.config.pipeline)
        
        # Classification Prompt Template (Similar to Generation but for Inference)
        # We explicitly inject strict rules.
        system_prompt = """You are an expert fraud investigator analyzing the Enron email corpus. 
        Your goal is to identify EMAILS WRITTEN BY EMPLOYEES that indicate fraud, evasion, or collusion.
        
        Classify the email into one of these categories:
        
        1. 'Evasion Attempt': The sender is explicitly trying to move conversation to a non-recorded channel (cell, home, offline) or destroy evidence ("shred", "delete").
        2. 'Fraud/Collusion': The email explicitly discusses known fraud entities (LJM, Raptor, Chewco, JEDI) or suspicious mechanisms (SPEs, off-balance-sheet) IN A BUSINESS CONTEXT.
        3. 'Business as Usual': Normal corporate communication, personal chatter, scheduling, OR publicly available NEWSLETTERS/ARTICLES.
        
        CRITICAL RULES:
        - If the email is a News Digest, Newsletter, or forwarded Press/Media article: Label as 'Business as Usual'.
        - If the email contains 'LJM', 'Raptor', 'Chewco' and is an internal discussion: Label as 'Fraud/Collusion'.
        - If the email says "call my cell" or "take offline" in the context of a sensitive deal: Label as 'Evasion Attempt'.
        
        Return stricly valid JSON matching this schema: {'classification': str, 'reasoning': str, 'confidence': float}
        """

        results = []
        metrics = {"total": 0, "correct": 0, "errors": 0}
        
        for i, item in enumerate(dataset):
            email_body = item.get("full_body_snippet", item.get("input", ""))
            expected_label = item.get("actual_output") # In Golden Dataset v1, 'actual_output' is the correct label
            
            logger.info(f"Processing {i+1}/{len(dataset)}...")
            
            prompt = f"{system_prompt}\n\nEMAIL:\n{email_body}\n\nJSON Response:"
            
            try:
                response = llm.complete(prompt)
                content = response.text
                
                # Cleanup JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()
                
                try:
                    prediction_json = json.loads(content)
                    predicted_label = prediction_json.get("classification", "Unknown")
                    reasoning = prediction_json.get("reasoning", "")
                except json.JSONDecodeError:
                    predicted_label = "Error"
                    reasoning = "JSON Decode Failure"
                    metrics["errors"] += 1
                
                is_correct = (predicted_label.lower() == expected_label.lower())
                
                if is_correct:
                    metrics["correct"] += 1
                
                metrics["total"] += 1
                
                results.append({
                    "id": item.get("metadata", {}).get("message_id", f"sample_{i}"),
                    "input_snippet": email_body[:100],
                    "expected": expected_label,
                    "predicted": predicted_label,
                    "reasoning": reasoning,
                    "correct": is_correct
                })
                
                logger.info(f"   Expected: {expected_label} | Predicted: {predicted_label} | Correct: {is_correct}")
                
            except Exception as e:
                logger.error(f"Error: {e}")
                results.append({
                    "id": item.get("metadata", {}).get("message_id", f"sample_{i}"),
                    "error": str(e)
                })

        # Calculate Metrics
        accuracy = metrics["correct"] / metrics["total"] if metrics["total"] > 0 else 0
        logger.info(f"=== Experiment Complete ===")
        logger.info(f"Accuracy: {accuracy:.2%} ({metrics['correct']}/{metrics['total']})")
        
        # Save Results
        self._save_results(results, accuracy)

    def _save_results(self, results, accuracy):
        output_dir = Path(self.config.output_dir) if self.config.output_dir else self.config_path.parent / "results"
        if not output_dir.is_absolute():
            output_dir = self.config_path.parent / self.config.output_dir
            
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.name}_{timestamp}.json"
        
        final_output = {
            "config": self.config.dict(),
            "metrics": {"accuracy": accuracy},
            "results": results
        }
        
        with open(output_dir / filename, 'w') as f:
            json.dump(final_output, f, indent=2)
            
        logger.info(f"Results saved to {output_dir / filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    
    asyncio.run(IntentExperimentRunner(args.config).run())
