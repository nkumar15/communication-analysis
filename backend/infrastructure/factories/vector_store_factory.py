import os
from llama_index.core.vector_stores.types import VectorStore
# from llama_index.vector_stores.elasticsearch import ElasticsearchStore
# from llama_index.vector_stores.postgres import PGVectorStore
# Using deferred imports to avoid hard crashes if dependencies missing during dev

class VectorStoreFactory:
    @staticmethod
    def get_vector_store(index_name: str) -> VectorStore:
        """
        Returns a configured LlamaIndex VectorStore instance.
        Default: Elasticsearch
        """
        provider = os.getenv("VECTOR_STORE_PROVIDER", "elasticsearch").lower()
        
        if provider == "elasticsearch":
            from llama_index.vector_stores.elasticsearch import ElasticsearchStore
            
            es_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
            return ElasticsearchStore(
                es_url=es_url,
                index_name=index_name,
            )
            
        elif provider == "postgres":
            from llama_index.vector_stores.postgres import PGVectorStore
            
            # Construct async connection string or use settings
            # PGVectorStore typically needs sync psycopg2 driver or asyncpg depending on impl
            # For now assume mostly standard usage
            db_host = os.getenv("POSTGRES_SERVER", "db")
            db_user = os.getenv("POSTGRES_USER", "postgres")
            db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
            db_name = os.getenv("POSTGRES_DB", "app")
            
            url = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"
            
            return PGVectorStore(
                connection_string=url,
                table_name=index_name, # Map index_name to table
                schema_name="b2b", # Creating in b2b schema as per plan
                embed_dim=384 # Default for bge-small-en-v1.5
            )
            
        else:
            raise ValueError(f"Unsupported Vector Store provider: {provider}")
