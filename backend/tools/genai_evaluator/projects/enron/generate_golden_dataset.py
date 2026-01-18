import pandas as pd
import json
import os
import random
import sys
import re
from typing import List, Dict
from pydantic import BaseModel, Field

# Adjust path: In Docker, /app is the root, so 'backend' is not in path.
# We need to import 'infrastructure' directly if /app is PYTHONPATH.
# OR if we want to keep 'backend.' syntax, we need to append parent of /app? 
# Usually in this codebase 'backend' IS the package. 
# Let's try adding /app to path (already there) and importing without 'backend' prefix OR 
# depending on how other modules do it. 
# Looking at other files, imports are usually absolute `backend.xxx`. 
# This implies the ROOT of the project is in PYTHONPATH. 
# In Docker `domain-api`, PYTHONPATH might be `/app`.
# Let's check if we can simply strip `backend.` or if we need to set PYTHONPATH.

# Try robust import
try:
    from backend.infrastructure.factories.llm_factory import LLMFactory
except ImportError:
    # If running inside container where 'backend' package is not resolved (e.g. /app is root)
    # We might need to add the parent directory to sys.path, or import as absolute from current root
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))
    try:
        from backend.infrastructure.factories.llm_factory import LLMFactory
    except ImportError:
        # Fallback for Docker /app root
        sys.path.append("/app") 
        from infrastructure.factories.llm_factory import LLMFactory

# --- Configurations ---
DATASET_DIR = "scripts/evaluation/datasets/enron" # Relative to /app in Docker
# Check if running locally or in docker for paths
if not os.path.exists(DATASET_DIR) and os.path.exists(f"backend/{DATASET_DIR}"):
     DATASET_DIR = f"backend/{DATASET_DIR}"

SOURCE_CSV = os.path.join(DATASET_DIR, "source/emails_flattened.csv")
OUTPUT_JSON = os.path.join(DATASET_DIR, "golden_dataset/enron_intent_golden_v2.json")

# Keywords based on Enron Fraud Research
KEYWORDS_ENTITIES = ["LJM", "LJM1", "LJM2", "Raptor", "Chewco", "JEDI", "Whitewing", "Osprey"]
KEYWORDS_MECHANICS = ["Special Purpose Entity", "SPE", "off balance sheet", "mark to market", "Prepays"]
KEYWORDS_EVASION = ["take this offline", "take it offline", "call my cell", "home phone", "destroy", "shred", "don't put in writing", "delete this email"]

# News Filtering (Negative Keywords)
KEYWORDS_NEWS = ["Dow Jones", "Reuters", "Bloomberg", "Copyright", "Newsletter", "Unsubscribe", "All rights reserved", "Associated Press", "Chronicle", "Times"]

# Target Counts
COUNT_SUSPICIOUS = 80
COUNT_BENIGN = 20

class IntentLabel(BaseModel):
    classification: str = Field(..., description="The classification of the email: 'Evasion Attempt', 'Fraud/Collusion', or 'Business as Usual'")
    reasoning: str = Field(..., description="Explanation of why this label was chosen, citing specific phrases.")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")

def load_data():
    if not os.path.exists(SOURCE_CSV):
        raise FileNotFoundError(f"Source CSV not found: {SOURCE_CSV}")
    
    # Read CSV
    df = pd.read_csv(SOURCE_CSV, on_bad_lines='skip')
    df = df.dropna(subset=['body'])
    return df

def sample_emails(df):
    """
    Selects a mix of keyword-heavy (suspicious) and random (benign) emails.
    """
    print("🔍 Sampling emails...")
    
    # 1. Suspicious Sampling
    all_keywords = KEYWORDS_ENTITIES + KEYWORDS_MECHANICS + KEYWORDS_EVASION
    # Escape keywords and add word boundaries \b
    pattern = '|'.join([rf"\b{re.escape(k)}\b" for k in all_keywords])
    
    # Positive Filter
    suspicious_mask = df['body'].str.contains(pattern, case=False, regex=True, na=False)
    
    # Negative Filter (Remove News/Marketing)
    news_pattern = '|'.join([re.escape(k) for k in KEYWORDS_NEWS])
    news_mask = df['body'].str.contains(news_pattern, case=False, regex=True, na=False)
    
    suspicious_df = df[suspicious_mask & ~news_mask]
    
    if len(suspicious_df) < COUNT_SUSPICIOUS:
        print(f"⚠️  Only found {len(suspicious_df)} suspicious emails (Target: {COUNT_SUSPICIOUS}). Taking all.")
        sampled_suspicious = suspicious_df
    else:
        sampled_suspicious = suspicious_df.sample(n=COUNT_SUSPICIOUS, random_state=42)

    # 2. Benign Sampling
    # Benign can be anything that is NOT suspicious (or is suspicious but filtered as news, though news is effectively benign BAU)
    # To be safe, let's just sample from anything NOT in our selected suspicious set
    
    # Drop rows already selected as suspicious
    remaining_df = df.drop(sampled_suspicious.index)
    sampled_benign = remaining_df.sample(n=COUNT_BENIGN, random_state=42)
    
    combined_df = pd.concat([sampled_suspicious, sampled_benign])
    combined_df = combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    print(f"✅ Selected {len(combined_df)} emails ({len(sampled_suspicious)} likely suspicious, {len(sampled_benign)} likely benign).")
    return combined_df

def label_with_llm(row) -> Dict:
    """
    Uses LLMFactory to label a single email.
    """
    email_text = f"Subject: {row['subject']}\nFrom: {row['sender']}\nTo: {row['recipients']}\n\n{row['body']}"
    if len(email_text) > 4000:
        email_text = email_text[:4000] + "...[TRUNCATED]"

    system_prompt = """You are an expert fraud investigator analyzing the Enron email corpus. 
    Classify the following email into one of these categories:
    1. 'Evasion Attempt': The sender is trying to move conversation to a non-recorded channel (cell, home, offline) or destroy evidence.
    2. 'Fraud/Collusion': The email explicitly discusses known fraud entities (LJM, Raptor, Chewco) or suspicious financial mechanisms (SPEs, off-balance-sheet).
    3. 'Business as Usual': Normal corporate communication, meeting scheduling, or personal chatter unrelated to fraud.
    """
    
    
    # Use Factory to get model
    try:
        llm = LLMFactory.get_llm() 
        
        # Enhanced System Prompt with specific instruction on Entities vs News
        system_prompt = """You are an expert fraud investigator analyzing the Enron email corpus. 
        Your goal is to identify EMAILS WRITTEN BY EMPLOYEES that indicate fraud, evasion, or collusion.
        
        Classify the email into one of these categories:
        
        1. 'Evasion Attempt': The sender is explicitly trying to move conversation to a non-recorded channel (cell, home, offline) or destroy evidence ("shred", "delete").
        2. 'Fraud/Collusion': The email explicitly discusses known fraud entities (LJM, Raptor, Chewco, JEDI) or suspicious mechanisms (SPEs, off-balance-sheet) IN A BUSINESS CONTEXT (e.g. valid deals, structuring, approvals).
        3. 'Business as Usual': Normal corporate communication, personal chatter, scheduling, OR publicly available NEWSLETTERS/ARTICLES even if they mention fraud keywords.
        
        CRITICAL RULES:
        - If the email is a News Digest, Newsletter, or forwarded Press/Media article: Label as 'Business as Usual' UNLESS the sender adds specific commentary endorsing or planning fraud.
        - If the email contains 'LJM', 'Raptor', 'Chewco' and is an internal discussion about structuring, approvals, or checking logic: Label as 'Fraud/Collusion'.
        - If the email says "call my cell" or "take offline" in the context of a sensitive deal: Label as 'Evasion Attempt'.
        """

        prompt = f"{system_prompt}\n\nEMAIL:\n{email_text}\n\nReturn strictly valid JSON matching this schema: {{'classification': str, 'reasoning': str, 'confidence': float}}"
        
        response = llm.complete(prompt)
        content = response.text
        
        # Clean markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        result = json.loads(content)
        
        # Fix: Include mechanics in keywords check
        all_keywords = KEYWORDS_ENTITIES + KEYWORDS_EVASION + KEYWORDS_MECHANICS
        
        return {
            "input": row['body'][:1000],
            "full_body_snippet": email_text[:2000],
            "actual_output": result.get("classification", "Unknown"),
            "reasoning": result.get("reasoning", ""),
            "metadata": {
                "message_id": row['message_id'],
                "sender": row['sender'],
                "evidence_confidence": result.get("confidence", 0.0),
                "keywords_found": [k for k in all_keywords if re.search(rf"\b{re.escape(k)}\b", str(row['body']), re.IGNORECASE)]
            }
        }
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return None

def generate_dataset():
    # Adjust path if running in Docker with /app as root
    if not os.path.exists(SOURCE_CSV):
        print(f"❌ Source CSV not found at {SOURCE_CSV}")
        return

    df = load_data()
    sampled_df = sample_emails(df)
    
    dataset = []
    print("🤖 Starting LLM Labeling (via LLMFactory)...")
    
    try:
        LLMFactory.get_llm()
    except Exception as e:
        print(f"❌ Error initializing LLMFactory: {e}")
        return

    for i, row in sampled_df.iterrows():
        print(f"   Processing {i+1}/{len(sampled_df)}: {row['message_id']}...")
        label_data = label_with_llm(row)
        if label_data:
            dataset.append(label_data)
            
    with open(OUTPUT_JSON, "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"\n✅ Golden Dataset saved: {OUTPUT_JSON}")
    print(f"   Total Samples: {len(dataset)}")

if __name__ == "__main__":
    generate_dataset()
