# Search & RAG

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Demonstrate AI power without gimmicks – positioned as research assistant, not decision-maker |
| **Target Persona** | Marcus Johnson (Analyst), Dr. Priya Sharma (Risk Officer) |
| **Permission** | `rag:read` |

## Two Search Modes

| Mode | Examples |
|------|----------|
| **Guided Questions** | "Show communications before earnings calls" |
| | "Find emails discussing off-book entities" |
| | "Who communicated most with [sender]?" |
| **Free-form Search** | Full-text semantic search with RAG synthesis |

## Constraints (Visible to User)

| Constraint | Description |
|------------|-------------|
| Region Scoped | Search limited to user's region access |
| Role Filtered | Results filtered by data access level |
| Audit Logged | Every query logged for compliance |
| Confidence Shown | AI responses include confidence score |

## User Stories

1. **As a Surveillance Analyst**, I want guided questions so that I can explore without knowing exact query syntax.
2. **As a Surveillance Analyst**, I want semantic search so that I can find conceptually similar content.
3. **As a Compliance Officer**, I want search queries audit-logged so that we can review analyst behavior.
4. **As a Surveillance Analyst**, I want AI confidence scores shown so that I know when to verify results.
5. **As a Risk Officer**, I want region scoping enforced so that data access policies are respected.

## UX Rules

- Always show constraints panel
- Confidence scores visible on every result
- "Research assistant, not decision-maker" positioning

## Demo Hook

> Guided question: "Show communications before earnings calls" → reveals pre-crisis patterns

## Wireframe

![Search & RAG Wireframe](../wireframes/search_rag.png)

## Technical Implementation

See [API Reference](../technical/api.md#search--rag)
