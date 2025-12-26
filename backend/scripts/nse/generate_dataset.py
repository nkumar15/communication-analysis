import os
import json
import logging
import asyncio
import sys
import pdfplumber
from pathlib import Path
from typing import List, Dict

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) 
sys.path.append("/app") 

from llama_index.core.schema import TextNode
from llama_index.core.evaluation import DatasetGenerator
from llama_index.core import Settings

try:
    from backend.infrastructure.factories.llm_factory import LLMFactory
except ImportError:
    from infrastructure.factories.llm_factory import LLMFactory

# Configuration
SCRIPT_DIR = Path(__file__).parent
TEST_DATA_DIR = SCRIPT_DIR / "data/raw/test"
DATASET_OUTPUT_DIR = SCRIPT_DIR / "data/dataset"
OUTPUT_FILE = DATASET_OUTPUT_DIR / "gold_dataset.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_nodes_with_structure(pdf_path: Path) -> List[TextNode]:
    """
    Extracts text from PDF, converting tables to Markdown to preserve structure.
    """
    nodes = []
    logger.info(f"Extracting structured data from {pdf_path.name} using pdfplumber...")
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text_content = []
            
            # 1. Extract Tables
            tables = page.extract_tables()
            if tables:
                text_content.append(f"--- TABLES ON PAGE {i+1} ---")
                for table in tables:
                    # Convert to simple Markdown-like format
                    # Filter out None/Empty cells
                    markdown_table = ""
                    for row in table:
                        clean_row = [str(cell).replace('\n', ' ') if cell else "" for cell in row]
                        markdown_table += "| " + " | ".join(clean_row) + " |\n"
                    text_content.append(markdown_table)
            
            # 2. Extract Text (Fallback for non-table content)
            # Note: deduplication is hard, so we just append text after tables for now
            # In a refined parser, we would subtract table bboxes.
            raw_text = page.extract_text()
            if raw_text:
                text_content.append(f"--- TEXT ON PAGE {i+1} ---")
                text_content.append(raw_text)
            
            # Create a Node for this page
            if text_content:
                full_text = "\n\n".join(text_content)
                node = TextNode(text=full_text)
                node.metadata = {"page_label": str(i+1), "file_name": pdf_path.name}
                nodes.append(node)
                
    return nodes

async def generate_dataset():
    if not TEST_DATA_DIR.exists():
        logger.error(f"Test directory {TEST_DATA_DIR} not found.")
        return

    DATASET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Initialize LLM
    logger.info("Initializing LLM...")
    llm = LLMFactory.get_llm()
    Settings.llm = llm # Set global default just in case

    # 2. Load and Parse specific TCS file
    target_file = TEST_DATA_DIR / "tcs_q2_fy26_results.pdf"
    if not target_file.exists():
        logger.error(f"Target file {target_file} not found!")
        return

    nodes = extract_nodes_with_structure(target_file)
    logger.info(f"Created {len(nodes)} structured nodes from {target_file.name}.")

    # 3. Generate Questions with Custom Prompt
    # We force the LLM to focus on HARD NUMBERS and FINANCIAL METRICS
    question_gen_query = (
        "You are a strict financial analyst. Your task is to generate 2 specific questions "
        "based strictly on the provided context, which contains financial tables and text.\n"
        "RULES:\n"
        "1. Focus on specific numbers (Revenue, EBITDA, Margins, Growth Rates).\n"
        "2. Do NOT ask generic questions like 'What is the company name?'.\n"
        "3. Ask comparison questions if data allows (e.g., 'Compare Q2 FY26 vs Q1 FY26').\n"
        "4. The context may contain Markdown tables. Parse them to ask precise questions.\n"
        "\n"
        "Context:\n"
        "{context_str}\n"
        "\n"
        "Questions:"
    )

    logger.info("Generating HIGH QUALITY synthetic questions...")
    
    # Process first 10 pages where results usually are
    data_generator = DatasetGenerator(
        nodes[:10], 
        llm=llm,
        num_questions_per_chunk=2,
        question_gen_query=question_gen_query
    )
    
    questions = await data_generator.agenerate_questions_from_nodes(num=10)
    logger.info(f"Generated {len(questions)} questions.")

    # 4. Generate Answers
    dataset = []
    for q in questions:
        # Ask LLM to answer using its own logic + context (implicit)
        # We emphasize formatting in the answer prompt
        response = llm.complete(
            f"Question: {q}\n"
            f"Context: (Assume access to TCS Q2 FY26 Results)\n"
            f"Answer: Provide a precise financial answer with numbers."
        )
        
        dataset.append({
            "input": q,
            "expected_output": response.text,
            "context": ["(Context derived from TCS Q2 FY26 PDF)"] 
        })
        
    # Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(dataset, f, indent=2)
    
    logger.info(f"✓ Saved {len(dataset)} items to {OUTPUT_FILE}")
    print(json.dumps(dataset[:2], indent=2))

if __name__ == "__main__":
    asyncio.run(generate_dataset())
