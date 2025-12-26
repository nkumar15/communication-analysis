import requests
import time
import os
import sys

# Configuration
API_URL = "http://localhost:8003/api/domain/rag"
TEST_PDF_PATH = "/home/neeraj/codes/enterprisesso/backend/scripts/nse/data/raw/test/tcs_q2_fy26_results.pdf"
TENANT_ID = "05b51fa4-45f4-50c2-b3f4-4c122000347b" # Same as dev/test

def run_verification():
    print("--- Starting Production Verification (Smoke Test) ---")
    
    # 1. Check if file exists
    if not os.path.exists(TEST_PDF_PATH):
        print(f"❌ Test file not found: {TEST_PDF_PATH}")
        sys.exit(1)
        
    print(f"📄 Using file: {TEST_PDF_PATH}")
    
    # 2. Upload
    print("📤 Uploading document...")
    try:
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_PDF_PATH), f, 'application/pdf')}
            data = {
                'tenant_id': TENANT_ID, 
                'company_name': 'TCS', 
                'report_type': 'Financial Results', 
                'financial_period': 'Q2 FY26'
            }
            response = requests.post(f"{API_URL}/upload", files=files, data=data)
            
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.text}")
            sys.exit(1)
            
        print(f"✅ Upload successful. Response: {response.json()}")
        job_id = response.json().get("job_id")
        
    except Exception as e:
        print(f"❌ Upload Error: {e}")
        sys.exit(1)

    # 3. Poll Status
    print(f"⏳ Polling status for Job ID: {job_id}...")
    max_retries = 30
    for i in range(max_retries):
        try:
            status_resp = requests.get(f"{API_URL}/status/{job_id}", params={'tenant_id': TENANT_ID})
            status_data = status_resp.json()
            status = status_data.get("status")
            
            print(f"   [{i+1}/{max_retries}] Status: {status}")
            
            if status == "completed":
                print(f"✅ Ingestion Completed. Chunks: {status_data.get('chunks')}")
                break
            elif status == "failed":
                print(f"❌ Ingestion Failed: {status_data.get('error_message')}")
                sys.exit(1)
                
            time.sleep(2)
        except Exception as e:
             print(f"   Error checking status: {e}")
             time.sleep(2)
    else:
        print("❌ Timeout waiting for completion")
        sys.exit(1)

    # 4. Verification Search
    query = "What is the total income?"
    print(f"🔍 Verifying Search with query: '{query}'...")
    try:
        search_resp = requests.post(f"{API_URL}/search", data={
            'query': query,
            'tenant_id': TENANT_ID,
            'limit': 3
        })
        
        if search_resp.status_code != 200:
            print(f"❌ Search Request Failed: {search_resp.text}")
            sys.exit(1)
            
        results = search_resp.json().get("results", [])
        if not results:
             print("❌ API returned 0 results. Retrieval failed.")
             sys.exit(1)
             
        print(f"✅ Search Verified. Retrieved {len(results)} chunks.")
        print(f"   Top Result Score: {results[0].get('score')}")
        print(f"   Top Result Text Snippet: {results[0].get('text')[:100]}...")
        
    except Exception as e:
        print(f"❌ Search Error: {e}")
        sys.exit(1)

    print("\n🎉 PRODUCTION VERIFICATION SUCCESSFUL")

if __name__ == "__main__":
    run_verification()
