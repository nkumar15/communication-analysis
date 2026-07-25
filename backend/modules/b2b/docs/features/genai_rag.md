# GenAI RAG (Retrieval Augmented Generation)

> **Status**: ![Status](https://img.shields.io/badge/Status-Available-blue)

Domain capability for AI-powered analysis and chat.

## Quick Reference
- [Bank Surveillance RAG](../../domains/b2b/bank_surveillance/README.md)
- [RAG Architecture](../../domains/b2b/bank_surveillance/docs/technical/architecture.md)

## Overview
> [!NOTE]
> GenAI RAG is a **Domain Capability**, not a core B2B Foundation service. It is implemented within specific verticals like **Bank Surveillance**.

The RAG system enables Natural Language Querying (NLQ) over structured and unstructured tenant data.
- **Vector DB**: Pinecone / pgvector.
- **LLM**: OpenAI GPT-4 / Anthropic Claude.
- **Context**: Strict Tenant Isolation in vector space.

## Features
- **Smart Search**: Semantic search over emails, documents, and logs.
- **Summarization**: Auto-generate case summaries.
- **Q&A**: Chat interface for data interrogation.

## Security & Isolation
- **Namespace Isolation**: Every tenant gets a dedicated namespace or metadata filter in the Vector DB.
- **Punctuation**: GenAI queries pass through the standard RBAC layer (Middleware).

## How to Implement in New Domain

- [ ] **Ingestion Pipeline**: Create ETL jobs to chunk and embed data.
- [ ] **Vector Store**: Configure index with `tenant_id` metadata.
- [ ] **Retriever**: Implement RAG chain using LangChain/LlamaIndex.
