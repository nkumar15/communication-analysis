# LlamaIndex Advanced RAG Cheat Sheet
> **Focus**: Financial Analysis & Earnings Call RAG Implementation

This cheat sheet maps LlamaIndex's advanced capabilities to our specific financial domain needs, complete with code snippets.

---

## 1. ingestion & Parsing (Structure)

### 1.1 Semantic Chunking (`SemanticSplitterNodeParser`)
*   **What it is**: Splits text not by fixed character count, but by semantic similarity (embedding distance). Keeps related concepts together.
*   **Applicability**: Earnings calls have distinct sections (Outlook, Q&A, Financials). Semantic chunking prevents cutting a CEO's answer in half just because it hit 512 tokens.
*   **Code**:
    ```python
    from llama_index.core.node_parser import SemanticSplitterNodeParser
    from llama_index.embeddings.openai import OpenAIEmbedding

    embed_model = OpenAIEmbedding()
    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model
    )
    nodes = splitter.get_nodes_from_documents(documents)
    ```

### 1.2 Node Parsers (Hierarchical & Sentence Window)
*   **What it is**:
    *   **Hierarchical**: Creates parent-child relationships (e.g., Document -> Section -> Paragraph).
    *   **Sentence Window**: Splits into single sentences but keeps a "window" of surrounding sentences as metadata for context during synthesis.
*   **Applicability**:
    *   *Hierarchical*: Good for "Summarize the Q&A section" (Parent) vs "What was the margin?" (Child).
    *   *Sentence Window*: Pinpoint accuracy for "What is the text of footnote 3?" while generating with full context.
*   **Code**:
    ```python
    from llama_index.core.node_parser import SentenceWindowNodeParser

    # Creates nodes with 3 sentences before/after
    node_parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )
    ```

### 1.3 Metadata Extraction
*   **What it is**: Uses LLMs to extract structured tags (Ticker, Year, Tone) during ingestion.
*   **Applicability**: Essential for filtering. "Revenue for TCS" must filter by `ticker: TCS`.
*   **Code**:
    ```python
    from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor

    extractors = [
        TitleExtractor(nodes=5),
        QuestionsAnsweredExtractor(questions=3),
    ]
    # Applied during ingestion pipeline
    ```

---

## 2. Retrieval (Precision)

### 2.1 Auto-Merging Retriever
*   **What it is**: Retrieves small leaf chunks. If enough leaves from the same parent are retrieved, it merges them and retrieves the *Parent* node instead.
*   **Applicability**: If a user asks a broad question, small chunks might miss the big picture. This automatically "zooms out" to the section level.
*   **Code**:
    ```python
    from llama_index.core.retrievers import AutoMergingRetriever

    retriever = AutoMergingRetriever(
        vector_retriever, 
        storage_context=storage_context, 
        verbose=True
    )
    ```

### 2.2 Ensemble Retriever
*   **What it is**: Combines results from multiple retrievers (e.g., BM25 + Vector) using logic like RRF (Reciprocal Rank Fusion).
*   **Applicability**: "EBITDA of Reliance" (Keyword heavy) vs "How is the company growing?" (Semantic). Ensemble handles both.
*   **Code**:
    ```python
    from llama_index.core.retrievers import QueryFusionRetriever

    retriever = QueryFusionRetriever(
        [vector_retriever, bm25_retriever],
        similarity_top_k=10,
        num_queries=1,  # Can also generate sub-queries
        mode="reciprocal_rerank",
    )
    ```

### 2.3 Router Retriever
*   **What it is**: Dynamically chooses *which* retriever to use based on the query.
*   **Applicability**: Route "Summarize the document" to a SummaryIndex, and "Find specific fact" to a VectorIndex.
*   **Code**:
    ```python
    from llama_index.core.tools import RetrieverTool
    from llama_index.core.retrievers import RouterRetriever

    retriever = RouterRetriever(
        selector=PydanticSingleSelector.from_defaults(),
        retriever_tools=[
            RetrieverTool.from_defaults(keyword_retriever, description="Useful for specific keywords"),
            RetrieverTool.from_defaults(vector_retriever, description="Useful for semantic search"),
        ],
    )
    ```

---

## 3. Query Engines (Reasoning)

### 3.1 Sub-Question Query Engine
*   **What it is**: Breaks complex queries into sub-questions.
*   **Applicability**: "Compare TCS and Infosys margins". Decomposes to: 1. "Get TCS margin", 2. "Get Infosys margin".
*   **Code**:
    ```python
    from llama_index.core.query_engine import SubQuestionQueryEngine
    from llama_index.core.tools import QueryEngineTool

    query_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools=[tcs_tool, infosys_tool],
        llm=llm
    )
    ```

### 3.2 Citation Query Engine
*   **What it is**: Inserts inline citations `[1]` into the answer, linked to the source node.
*   **Applicability**: Compliance requirement. "According to the Q3 report [1], revenue is..."
*   **Code**:
    ```python
    from llama_index.core.query_engine import CitationQueryEngine

    query_engine = CitationQueryEngine.from_args(
        index,
        citation_chunk_size=512,
    )
    response = query_engine.query("What is the revenue?")
    print(response.source_nodes[0].node.get_content()) # Provenance
    ```

### 3.3 Retry Query Engine
*   **What it is**: If the initial evaluation (self-correction) deems the answer poor, it re-generates the query or response.
*   **Applicability**: "Refines" hallucinations. If the LLM generates a number not in the context, the Retry engine catches it.
*   **Code**:
    ```python
    from llama_index.core.query_engine import RetryQueryEngine
    from llama_index.core.evaluation import RelevancyEvaluator

    query_engine = RetryQueryEngine(
        base_query_engine=vector_query_engine,
        evaluator=RelevancyEvaluator(),
    )
    ```

---

## 4. Response Synthesis (Generation)

### 4.1 Tree Summarize
*   **What it is**: Recursively summarizes chunks until they fit in context.
*   **Applicability**: "Summarize the entire 50-page transcript".
*   **Code**: `get_response_synthesizer(response_mode="tree_summarize")`

### 4.2 Refine
*   **What it is**: Generates an answer from chunk 1, passes it to chunk 2 to "refine" it, and so on.
*   **Applicability**: detailed answers requiring information spread across the text.
*   **Code**: `get_response_synthesizer(response_mode="refine")`

### 4.3 Compact
*   **What it is**: Stuffs as many chunks as possible into the context window before generation. Detailed and cheap.
*   **Applicability**: General purpose Q&A (Default).
*   **Code**: `get_response_synthesizer(response_mode="compact")`
