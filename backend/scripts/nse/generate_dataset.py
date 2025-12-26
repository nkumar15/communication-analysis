import os
import glob
import json
import logging
import asyncio
from typing import List, Dict
from pathlib import Path

# Placeholder for real generation using LlamaIndex/DeepEval
# In Phase 3 step 2, we will add the heavy ML logic.
# This script currently scans the source directory and prepares the structure.

DATA_SOURCE_DIR = Path("backend/scripts/nse/data/source")
DATASET_OUTPUT_DIR = Path("backend/scripts/nse/data/dataset")
OUTPUT_FILE = DATASET_OUTPUT_DIR / "gold_dataset.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scan_documents() -> List[Path]:
    """Find all supported documents in source directory"""
    extensions = ["*.pdf", "*.txt"]
    files = []
    for ext in extensions:
        files.extend(DATA_SOURCE_DIR.glob(ext))
    return files

async def generate_synthetics(files: List[Path]):
    """
    Generate synthetic Q&A pairs.
    TODO: Integrate LlamaIndex/DeepEval here.
    """
    dataset = []
    
    logger.info(f"Found {len(files)} documents: {[f.name for f in files]}")
    
    for file_path in files:
        logger.info(f"Processing {file_path.name}...")
        
        # Stub logic for now
        # Real logic: Load doc -> Chunk -> Gen Questions -> Gen Answers
        
        doc_id = file_path.stem
        # 5 Factoid Questions
        for i in range(5):
            dataset.append({
                "id": f"{doc_id}_fact_{i}",
                "query": f"Sample Fact Question {i} for {doc_id}?",
                "expected_output": f"Sample Fact Answer {i}",
                "context": f"Excerpt from {file_path.name} page {i}",
                "source_doc": file_path.name,
                "type": "fact"
            })
            
    return dataset

def save_dataset(dataset: List[Dict]):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(dataset, f, indent=2)
    logger.info(f"Saved {len(dataset)} items to {OUTPUT_FILE}")

async def main():
    if not DATA_SOURCE_DIR.exists():
        logger.error(f"Source directory {DATA_SOURCE_DIR} does not exist.")
        return

    DATASET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    files = scan_documents()
    if not files:
        logger.warning("No files found via scan. Please download samples properly.")
        # We will allow empty run just to scaffolding
    
    dataset = await generate_synthetics(files)
    save_dataset(dataset)

if __name__ == "__main__":
    asyncio.run(main())
