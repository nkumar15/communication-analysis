# Policies

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Configure how risk is detected (Keywords, Semantic Rules, Models) |
| **Target Persona** | Dr. Priya Sharma (Risk Officer) |
| **Permission** | `policy:manage` |

## Features/Widgets

| Feature | Description |
|---------|-------------|
| Rule Editor | Create/Edit risk rules (Keyword, Regex, Semantic) |
| Simple Lexicon | List of banned words (e.g., "bribe", "guarantee") |
| Semantic Rules | Vector-based similarity rules (e.g., "promising definite return") |
| Risk Score Config | Assign severity/score to rules (Low, Medium, High) |
| Policy Versioning | Audit trail of active rules over time |
| **Regulatory Knowledge Base** | Ingestion of external PDF/Text policies (MAS, SEC, FCA) |
| **Compliance Mapping** | AI Mapping of detected risks to specific regulatory clauses |

## Regulatory Knowledge Base (RAG)

The system ingests external governance documents to contextualize risks:

**Supported Frameworks**:
- **SEC** (US): Rule 10b-5 (Employment of Manipulative and Deceptive Practices).
- **MAS** (Singapore): Securities and Futures Act (SFA) - Part XII Market Conduct.
- **FCA** (UK):  Market Abuse Regulation (MAR).

**Workflow**:
1. **Ingest**: Compliance Officer uploads PDF (e.g., "MAS Blue Book").
2. **Index**: System chunks and vectorizes the policy text.
3. **Map**: When a risk is detected (e.g., "Front Running"), the AI queries the knowledge base: *"Which MAS guideline prohibits this behavior?"*.
4. **Cite**: The Alert includes a citation: *"Potential violation of MAS SFA Section 197 (False Trading)."*

## Risk Theme & Detection Strategy (Enron Methodology)

The system uses a hierarchical approach: **Risk Theme** (High-level category) → **Risk Label** (Specific behavior).

| Risk Theme | Risk Label | Detection Technique | Primary Regulation (Example) | Enron Indicators / Examples |
|------------|------------|---------------------|------------------------------|-----------------------------|
| **Market Manipulation** | **Gaming Strategies** | Keyword (Exact) | FERC Anti-Manipulation Rule | "Death Star", "Get Shorty", "Ricochet", "Fat Boy" (Named schemes) |
| **Market Manipulation** | **Load Shifting** | GenAI (Semantic) | FERC / CAISO Tariffs | Discussions about moving power out of state to artificiality inflate prices. |
| **Market Manipulation** | **Front Running** | GenAI (Temporal) | SEC Rule 10b-5 / MAS SFA | Trading ahead of client orders or public announcements. |
| **Financial Fraud** | **Off-Balance Sheet** | Keyword + Graph | SOX Section 401 | "LJM", "Raptor", "Chewco", "SPV" (Hidden debt entities) |
| **Financial Fraud** | **Mark-to-Market** | GenAI (Intent) | IAS 39 / FAS 157 | Aggressive booking of future hypothetical profits as current revenue. |
| **Conflict of Interest** | **Analyst Pressure** | GenAI (Sentiment) | Global Research Settlement | Traders pressuring Research Analysts to upgrade stock ratings. |
| **Conflict of Interest** | **Auditor Independence** | GenAI (Semantic) | SOX Title II | Arthur Andersen partners discussing document destruction. |
| **Evasion & Secrecy** | **Channel Hopping** | GenAI (Intent) | SEC Rule 17a-4 | "Take this offline", "Call my cell", "Use personal email". |
| **Evasion & Secrecy** | **Evidence Destruction**| Keyword (Fuzzy) | 18 U.S.C. § 1519 | "Delete this email", "Shred", "No paper trail". |
| **Toxic Culture** | **Intimidation** | GenAI (Sentiment) | Hostile Work Environment | bullying, aggressive language, "Step on their throat". |

## User Stories

1. **As a Risk Officer**, I want to filter alerts by **Risk Theme** (e.g., "Conflict of Interest") so I can see systemic issues across the bank.
2. **As a Compliance Head**, I want to deploy "GenAI Semantic" rules to catch **Load Shifting** discussions that don't use specific code words.
3. **As a Surveillance Analyst**, I want the system to flag "Channel Hopping" attempts so I can investigate the off-channel communications.
2. **As a Data Scientist**, I want to configure an "Embedding-based Rule" so that I can catch subtle forms of misconduct (semantic similarity).
3. **As a Compliance Officer**, I want to assign a risk score to each rule so that we prioritize the most critical alerts.
4. **As a Risk Manager**, I want to view rule versions so that I can prove which rules were active during a past audit period.
5. **As an Analyst**, I want to provide feedback on false positives so that the system improves accuracy over time.

## UX Rules

- **Explainability**: Rules must explicitly state *why* they match (e.g., "Matched keyword 'guarantee'", "85% similarity to 'insider trading' concept").
- **Impact Preview**: Show estimated alert volume *before* enabling a new rule.
- **Strict Versioning**: Never "edit" a comprehensive policy in place; create a new version.

## Wireframe

![Policies Wireframe](../wireframes/policies.png)

## Technical Implementation

- **Storage**: `policy_rules` table (JSONB for complex criteria)
- **Engine**: Hybrid matcher (Keyword regex + Vector cosine similarity)
- **Feedback**: `alert_feedback` table linked to rule ID

See [API Reference](../technical/api.md#policies)
