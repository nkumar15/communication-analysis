
import os
import re
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from llama_index.core.schema import TextNode
from llama_index.core.evaluation import DatasetGenerator
from llama_index.core import Settings
try:
    from backend.infrastructure.factories.llm_factory import LLMFactory
except ImportError:
    from infrastructure.factories.llm_factory import LLMFactory

# Configuration
SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DOCS_DIR = SCRIPT_DIR.parent / "datasets/nse/source_documents/test"
OUTPUT_DIR = SCRIPT_DIR.parent / "datasets/nse/golden_datasets"
OUTPUT_FILE = OUTPUT_DIR / "unified_gold_dataset.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentGroup:
    def __init__(self, key: str):
        self.key = key  # e.g. "tcs_q2_fy26"
        self.earnings_path: Optional[Path] = None
        self.concall_path: Optional[Path] = None

    @property
    def is_complete(self) -> bool:
        return self.earnings_path is not None and self.concall_path is not None

def parse_filename(filename: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parses filename to extract (ticker, type, period).
    Expected formats: 
    - tcs_earnings_q2_fy26_results.md
    - tcs_concall_Q2_FY26.md
    """
    # Normalize: lowercase
    clean_name = filename.lower()
    
    # Extract Ticker
    tickers = ["tcs", "infosys", "reliance", "hdfc", "fortis"]
    ticker = next((t for t in tickers if t in clean_name), None)
    
    # Extract Type
    doc_type = None
    if "concall" in clean_name:
        doc_type = "concall"
    elif "earnings" in clean_name or "results" in clean_name:
        doc_type = "earnings"
        
    # Extract Period (Q2_FY26)
    # Regex for q\d and fy\d+
    q_match = re.search(r"q\d", clean_name)
    fy_match = re.search(r"fy\d+", clean_name)
    
    period = f"{q_match.group(0)}_{fy_match.group(0)}" if q_match and fy_match else None
    
    return ticker, doc_type, period

def scan_directory(directory: Path) -> Dict[str, DocumentGroup]:
    groups = {}
    logger.info(f"Scanning {directory}...")
    
    for f in directory.glob("*.md"):
        ticker, doc_type, period = parse_filename(f.name)
        if not (ticker and doc_type and period):
            logger.warning(f"Could not parse filename: {f.name}")
            continue
            
        key = f"{ticker}_{period}"
        if key not in groups:
            groups[key] = DocumentGroup(key)
            
        if doc_type == "earnings":
            groups[key].earnings_path = f
        elif doc_type == "concall":
            groups[key].concall_path = f
            
    return groups

def extract_text_from_file(file_path: Path, max_chars: int = 100000) -> str:
    """Read text from Markdown file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            return content[:max_chars] # Truncate if huge
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return ""

async def generate_unified_dataset():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Init LLM
    llm = LLMFactory.get_llm()
    Settings.llm = llm
    
    # 2. Group Documents
    if not SOURCE_DOCS_DIR.exists():
        logger.error(f"Source dir {SOURCE_DOCS_DIR} does not exist")
        return

    groups = scan_directory(SOURCE_DOCS_DIR)
    dataset = []
    
    for key, group in groups.items():
        if not group.is_complete:
            logger.warning(f"Skipping incomplete group {key}: Earnings={group.earnings_path}, Concall={group.concall_path}")
            continue
            
        logger.info(f"Processing Group: {key}")
        
        # 3. Extract Contexts
        # Drastic reduction for debugging
        earnings_text = extract_text_from_file(group.earnings_path, max_chars=5000)
        concall_text = extract_text_from_file(group.concall_path, max_chars=5000)
        
        if not earnings_text or not concall_text:
            continue
            
        # 4. Generate Unified Questions
        prompt = (
            "You are a Senior Financial Analyst combining data from an Earnings Report and a Conference Call.\n"
            "Your goal is to generate 'Multi-Hop' questions that require BOTH sources to answer.\n"
            "\n"
            "--- CONTEXT A: EARNINGS REPORT (Quantitative) ---\n"
            f"{earnings_text}\n" 
            "\n"
            "--- CONTEXT B: CONCALL TRANSCRIPT (Qualitative) ---\n"
            f"{concall_text}\n"
            "\n"
            "RULES:\n"
            "1. Generate 8 complex questions.\n"
            "2. Each question MUST require a number from Context A and an explanation from Context B.\n"
            "   - Bad: 'What is revenue?' (Only A)\n"
            "   - Bad: 'What did the CEO say?' (Only B)\n"
            "   - Good: 'Revenue grew 12% (Context A), what specific 'headwinds' did the CEO cite (Context B) as the reason for missing the higher target?'\n"
            "3. Output ONLY valid JSON list: [{\"question\": \"...\"}, ...]\n"
        )
        
        try:
            response = llm.complete(prompt)
            # Parse JSON - simple heuristic
            json_str = re.search(r"\[.*\]", response.text, re.DOTALL)
            if json_str:
                questions = json.loads(json_str.group(0))
                
                # 5. Generate Answers (Ground Truth)
                for q_obj in questions:
                    question = q_obj['question']
                    
                    # Ask LLM to answer using BOTH full contexts
                    # (We use slightly larger context chunks here for accuracy)
                    ans_prompt = (
                        f"Context A (Earnings):\n{earnings_text[:6000]}\n\n"
                        f"Context B (Concall):\n{concall_text[:6000]}\n\n"
                        f"Question: {question}\n\n"
                        "Answer (Cite both 'Report' and 'Transcript' in your answer):"
                    )
                    ans_response = llm.complete(ans_prompt)
                    
                    dataset.append({
                        "input": question,
                        "expected_output": ans_response.text,
                        "metadata": {
                            "ticker": parse_filename(group.earnings_path.name)[0],
                            "period": parse_filename(group.earnings_path.name)[2],
                            "source_types": ["earnings", "concall"],
                            "files": [group.earnings_path.name, group.concall_path.name]
                        }
                    })
                    logger.info(f"Generated ({len(dataset)}): {question}")
                    await asyncio.sleep(1) # Prevent rate limiting
            else:
                logger.warning(f"Failed to parse JSON from LLM response for {key}")
                
        except Exception as e:
            logger.error(f"Error generating for {key}: {e}")

    # Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(dataset, f, indent=2)
    logger.info(f"Saved {len(dataset)} unified questions to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(generate_unified_dataset())
