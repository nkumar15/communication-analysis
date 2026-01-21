# Regulatory Library

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Central repository for regulatory frameworks and governance documents |
| **Target Persona** | Dr. Priya Sharma (Risk Officer), Head of Compliance |
| **Permission** | `regulatory:manage` |

## Features/Widgets

| Feature | Description |
|---------|-------------|
| **Document Ingestion** | Upload regulatory PDFs (SEC, MAS, FCA) with automatic chunking and vector indexing. |
| **Metadata Tagging** | Assign Framework (e.g., MAS), Region (e.g., Singapore), and Year to uploaded documents. |
| **Version Control** | Manage multiple versions of the same regulatory guideline as they evolve. |
| **Citation Search** | Directly search for specific clauses or sections within the library via RAG. |

## User Stories

1. **As a Risk Officer**, I want to upload the latest **MAS Blue Book** so that our Surveillance Controls can reference updated guidelines.
2. **As a Compliance Officer**, I want to tag regulatory documents by region so that our global desks are mapped to the correct legal framework.
3. **As a Surveillance Manager**, I want to see which specific section of the **SEC Rule 10b-5** triggered an alert citation.

## UX Rules

- **Source Integrity**: Always display the source PDF link alongside any AI-generated summary or citation.
- **Processing Status**: Show a progress bar during "Vector Indexing" to manage user expectations for large documents.

## Technical Implementation

- **Storage**: `regulatory_documents` table for metadata; Vector Store (Elasticsearch/pgvector) for content chunks.
- **RAG Engine**: LlamaIndex for document ingestion and cross-referencing.

See [API Reference](../technical/api.md#regulatory-library)
