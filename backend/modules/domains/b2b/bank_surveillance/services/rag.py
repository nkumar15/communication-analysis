import re
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import VectorStoreIndex
from typing import Dict, Any, List, Optional
from uuid import UUID
from modules.domains.shared.services.base_rag_service import BaseRagService

class CommunicationRagService(BaseRagService):
    _vector_store_provider = "elasticsearch"

    def get_index_name(self) -> str:
        return "communications"

    def get_parser(self):
        # Use simple sentence splitter for chunks
        return SentenceSplitter(chunk_size=512, chunk_overlap=50)

    async def search(self, query: str, tenant_id: UUID, limit: int = 5, access_scopes: Optional[List[UUID]] = None, **kwargs) -> Dict[str, Any]:
        """Basic RAG Search using Vector Store."""
        self._ensure_initialized()
        
        try:
            # 1. Setup Filters and Retriever
            from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter, MetadataFilter
            filters_list = [ExactMatchFilter(key="tenant_id", value=str(tenant_id))]
            if access_scopes:
                # Add regional filters for vector search
                scope_terms = [str(s) for s in access_scopes]
                filters_list.append(
                    MetadataFilter(key="data_region_id", value=scope_terms, operator="in")
                )

            filters = MetadataFilters(filters=filters_list)
            
            # For ES specifically, we can use the 'filters' arg in as_retriever if using LlamaIndex ES store
            index = VectorStoreIndex.from_vector_store(self.vector_store, embed_model=self.embed_model)
            retriever = index.as_retriever(similarity_top_k=limit, filters=filters)
            
            # 2. Retrieve
            nodes = await retriever.aretrieve(query)
            
            # 3. Format
            formatted_results = []
            for n in nodes:
                content = n.node.get_content()
                metadata = n.node.metadata
                metadata = self._enrich_metadata_for_display(content, metadata)
                
                formatted_results.append({
                    "text": content,
                    "score": n.score,
                    "metadata": metadata
                })
                
            return self._format_results(query, formatted_results)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._format_results(query, [])

    def _enrich_metadata_for_display(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures subject and other fields are populated for UI."""
        if not content:
            return metadata
            
        trimmed_content = content.strip()
        # Case insensitive check for "Subject: " in the first few lines
        if not metadata.get("subject") or metadata.get("subject") == "(No Subject)":
            lines = trimmed_content.split("\n")
            # Enron emails often have Subject line in the first 10 lines
            for line in lines[:10]:
                clean_line = line.strip()
                # Handle "Subject: ..." or "Subject:   ..."
                if clean_line.lower().startswith("subject:"):
                    metadata["subject"] = clean_line[8:].strip()
                    break
                # Some Enron emails use "Subject:	..." (tabbed)
                if clean_line.lower().startswith("subject"):
                    parts = re.split(r'[:\s\t]+', clean_line, maxsplit=1)
                    if len(parts) > 1 and parts[0].lower() == "subject":
                        metadata["subject"] = parts[1].strip()
                        break
        
        # Fallback values for UI
        metadata["subject"] = metadata.get("subject") or "(No Subject)"
        metadata["sender"] = metadata.get("sender") or "Unknown"
        metadata["recipients"] = metadata.get("recipients") or "Unknown"
        
        return metadata

    def _format_results(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "engine": "hybrid-search"
        }

    async def keyword_search(self, query: str, tenant_id: UUID, limit: int = 5, access_scopes: Optional[List[UUID]] = None) -> Dict[str, Any]:
        """Elasticsearch BM25 keyword search (No Embeddings, Cost Saving Demo)."""
        self._ensure_initialized()
        
        if self._vector_store_provider != "elasticsearch":
            # Fallback for other providers if needed, though we primarily use ES
            return self._format_results(query, [])

        try:
            client = self.vector_store.client
            index_name = self.get_index_name()
            
            # Use simple_query_string for more robust term matching in demo highlights
            es_query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "simple_query_string": {
                                    "query": query,
                                    "fields": ["content^5", "metadata.subject^3", "metadata.sender^2"],
                                    "default_operator": "or",
                                    "analyze_wildcard": True
                                }
                            }
                        ],
                        "filter": [
                            {"term": {"metadata.tenant_id.keyword": str(tenant_id)}}
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {"number_of_fragments": 3},
                        "metadata.subject": {}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                },
                "size": limit
            }
            
            if access_scopes:
                # Add regional filters to keyword search
                scope_terms = [str(s) for s in access_scopes]
                es_query["query"]["bool"]["filter"].append(
                    {"terms": {"metadata.data_region_id.keyword": scope_terms}}
                )
            
            response = await client.search(index=index_name, body=es_query)
            hits = response.get("hits", {}).get("hits", [])
            
            results = []
            for hit in hits:
                source = hit["_source"]
                content = source.get("content", "")
                metadata = source.get("metadata", {})
                metadata = self._enrich_metadata_for_display(content, metadata)
                
                # Capture highlights
                highlights = hit.get("highlight", {})
                
                results.append({
                    "text": content,
                    "score": hit["_score"],
                    "metadata": metadata,
                    "highlights": highlights
                })
                
            return self._format_results(query, results)
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return self._format_results(query, [])

    def _get_embedding_model(self, enable_semantic: bool):
        """
        Returns the appropriate embedding model based on regulation.
        - enable_semantic=True -> Real Embedding Model (e.g. OpenAI)
        - enable_semantic=False -> Mock Embedding (Keyword Only, Cost Saving)
        """
        if enable_semantic:
            return self.embed_model or EmbeddingFactory.get_embedding_model()
        else:
            from llama_index.core.embeddings import MockEmbedding
            # Use 1536 as safe default for OpenAI compatibility in ES mapping
            return MockEmbedding(embed_dim=1536)

    async def index_text(self, text: str, metadata: Dict[str, Any], doc_id: str = None, enable_semantic: bool = False) -> bool:
        """
        Index a single text document.
        Args:
            enable_semantic: If True, generate real embeddings. If False, use Mock (keyword only).
        """
        from llama_index.core import Document, StorageContext
        
        self._ensure_initialized()
        
        try:
            doc = Document(text=text, metadata=metadata, doc_id=doc_id)
            parser = self.get_parser()
            nodes = parser.get_nodes_from_documents([doc])
            
            # Select Model
            embed_model = self._get_embedding_model(enable_semantic)
            
            VectorStoreIndex(
                nodes,
                storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
                embed_model=embed_model, 
                show_progress=False
            )
            return True
        except Exception as e:
            print(f"Vector indexing failed: {e}")
            return False

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID (from vector store)."""
        # ... (Existing implementation unchanged) ...
        self._ensure_initialized()
        if self._vector_store_provider == "elasticsearch":
             pass # ...
        return None

    async def get_content_by_id(self, doc_id: str) -> Optional[str]:
        """Fetch full text content of a document by ID."""
        self._ensure_initialized()
        
        try:
            if self._vector_store_provider == "elasticsearch":
                # Access underlying ES client
                client = self.vector_store.client
                index_name = self.get_index_name()
                
                # LlamaIndex nodes have the original ID in metadata.message_id
                # Direct client.get(id=...) fails because ES _id is a node UUID.
                query = {
                    "query": {
                        "term": {
                            "metadata.message_id.keyword": doc_id
                        }
                    }
                }
                
                response = await client.search(index=index_name, body=query, size=1)
                hits = response.get("hits", {}).get("hits", [])
                
                if hits:
                    return hits[0]["_source"].get("content")
                
                # Try doc_id as fallback
                query["query"]["term"] = {"metadata.doc_id.keyword": doc_id}
                response = await client.search(index=index_name, body=query, size=1)
                hits = response.get("hits", {}).get("hits", [])
                if hits:
                    return hits[0]["_source"].get("content")
                
        except Exception as e:
            # Return None if not found or error
            return None
        return None

    async def index_batch(self, documents: List[Dict[str, Any]], enable_semantic: bool = False) -> int:
        """
        Batch index multiple documents.
        Args:
            enable_semantic: If True, generate real embeddings. If False, use Mock (keyword only).
        """
        from llama_index.core import Document, StorageContext
        
        self._ensure_initialized()
        
        docs = []
        for d in documents:
            docs.append(Document(
                text=d["text"], 
                metadata=d.get("metadata", {}),
                doc_id=d.get("doc_id") 
            ))
        
        parser = self.get_parser()
        nodes = parser.get_nodes_from_documents(docs)
        
        # Select Model
        embed_model = self._get_embedding_model(enable_semantic)
        
        VectorStoreIndex(
            nodes,
            storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
            embed_model=embed_model,
            show_progress=True
        )
        
        return len(docs)

    async def delete_documents(self, doc_ids: List[str]) -> bool:
        """
        Delete documents by ID from the vector store.
        Used for rollback/compensating transactions.
        """
        self._ensure_initialized()
        try:
             # LlamaIndex doesn't expose delete_nodes easily on VectorStoreIndex,
             # but we can use the underlying vector store client.
            if self._vector_store_provider == "elasticsearch":
                 client = self.vector_store.client
                 index_name = self.get_index_name()
                 
                 # Delete by API
                 for doc_id in doc_ids:
                     try:
                         await client.delete(index=index_name, id=doc_id)
                     except Exception:
                         # 404 is fine
                         pass
                 return True
            return False
        except Exception as e:
            print(f"Failed to delete documents: {e}")
            return False

# Singleton instance
communication_rag_service = CommunicationRagService()
