
import asyncio
import os
from elasticsearch import AsyncElasticsearch
from core.config import settings

async def main():
    es = AsyncElasticsearch(
        settings.elasticsearch_url,
        api_key=settings.elasticsearch_api_key
    )
    
    # We want to find documents associated with HDFC Q2 FY26
    # We don't have the exact file_path hash handy easily, but we can search by text content or filename metadata if stored.
    # BaseRagService usually stores 'file_name' in metadata.
    
    query = {
        "query": {
            "match": {
                "metadata.file_name": "hdfc_q2_fy26_presentation.pdf"
            }
        },
        "size": 5,
        "_source": ["metadata", "text"] # Only fetch metadata and snippet
    }
    
    print(f"Searching for hdfc_q2_fy26_presentation.pdf in index {settings.elasticsearch_index}...")
    try:
        response = await es.search(index=settings.elasticsearch_index, body=query)
        
        hits = response['hits']['hits']
        print(f"Found {len(hits)} hits.")
        
        for i, hit in enumerate(hits):
            print(f"\n--- Hit {i+1} ---")
            print(f"Metadata: {hit['_source'].get('metadata')}")
            print(f"Text Snippet: {hit['_source'].get('text')[:100]}...")
            
    except Exception as e:
        print(f"Error querying ES: {e}")
    finally:
        await es.close()

if __name__ == "__main__":
    import sys
    # Add backend path to sys.path
    sys.path.append(os.path.join(os.getcwd(), 'backend')) # Adjust if run from root
    
    asyncio.run(main())
