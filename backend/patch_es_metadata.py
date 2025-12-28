
import asyncio
import os
from elasticsearch import AsyncElasticsearch
from core.config import settings

async def main():
    # Use settings for consistent connection
    from elasticsearch import AsyncElasticsearch
    
    # Direct connection parameters if settings fail (assuming localhost from within container or mapped port)
    es = AsyncElasticsearch(
        "http://localhost:9200",
        # api_key=settings.elasticsearch_api_key 
    )
    
    index_name = "rag_documents"
    source_filename = "hdfc_q2_fy26_presentation.pdf"
    
    # 1. Verify we can find the docs
    query = {
        "query": {
            "match": {
                "metadata.source": source_filename
            }
        }
    }
    
    count = await es.count(index=index_name, body=query)
    print(f"Found {count['count']} chunks for {source_filename}")
    
    if count['count'] == 0:
        print("No documents found to patch!")
        await es.close()
        return

    # 2. Update by Query
    # We want to set ticker='HDFC', fiscal_year='FY26', quarter='Q2'
    # Based on filename hdfc_q2_fy26_presentation.pdf
    
    script = {
        "source": """
            ctx._source.metadata.ticker = params.ticker;
            ctx._source.metadata.company_name = params.company_name;
            ctx._source.metadata.fiscal_year = params.fiscal_year;
            ctx._source.metadata.quarter = params.quarter;
            ctx._source.metadata.scope = params.scope;
        """,
        "lang": "painless",
        "params": {
            "ticker": "HDFC",
            "company_name": "HDFC Bank",
            "fiscal_year": "FY26",
            "quarter": "Q2",
            "scope": ["Standalone", "Consolidated"] # Assumption based on usual reports
        }
    }
    
    print("Updating documents...")
    response = await es.update_by_query(
        index=index_name,
        body={
            "query": query['query'],
            "script": script
        },
        refresh=True
    )
    
    print(f"Update response: {response}")
    print(f"Updated {response['updated']} documents.")
    
    await es.close()

if __name__ == "__main__":
    import sys
    # Add backend path to sys.path
    sys.path.append(os.path.join(os.getcwd(), 'backend')) 
    asyncio.run(main())
