# AI Trust & Governance (AI Verify)

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Build trust by aligning GenAI detection with the **IMDA AI Verify** framework |
| **Pillars** | Explainability, Robustness, Transparency, Accountability |
| **Persona** | Compliance Officer, Regulator, AI Ethics Board |

## Alignment with AI Verify Pillars

To ensure our GenAI-based **Surveillance Controls** are trusted by banks, we implement the following features:

### 1. Explainability (The "Why" Widget)
- **Feature**: For every GenAI-triggered alert, the system generates a **Reasoning Path**.
- **Content**: It cites specific clauses from the **[Regulatory Library](./regulatory_library.md)** and quotes relevant snippets from the message that highlight the **Risk Indicator**.
- **Benefit**: Analysts don't have to guess; the AI provides the initial reasoning based on established law.

### 2. Robustness & Reliability (Semantic Consistency)
- **Feature**: **Detection Confidence Scoring**.
- **Content**: Indicators use "Consensus Voting" across multiple model passes to filter out hallucinations and transient risks.
- **Vetting**: We benchmark accuracy against the **Enron Ground Truth** set to prove a <5% False Positive rate (a key banking requirement).

### 3. Transparency & Auditability (Control Versioning)
- **Feature**: **Version History for Controls**.
- **Content**: Every change to a **Surveillance Control** (e.g., updating a prompt or adding a keyword) is logged with the ID of the Risk Officer who made the change.
- **Audit**: Regulators can see exactly which version of the "Front Running" control was active during a specific trading day.

### 4. Accountability (Human-in-the-Loop)
- **Feature**: **Decision Override & Feedback**.
- **Content**: AI flags *signals*, but only humans (Analysts) create *alerts* or *cases*. The "Feedback Loop" allows humans to correct the AI, with corrections stored for model re-tuning.

## Demo Embedding: "Trust Dashboard"

In the demo, we showcase trust through the following UI elements:

- **The Reasoning Sidebar**: Appears in the **[Alert View](./alerts.md)**.
- **AI Verify Scoreboard**: A dedicated summary page showing:
    - **Accuracy**: Hits vs. Misses on the Enron dataset.
    - **Drift**: Monitoring if the AI's understanding of "Market Abuse" changes over time.
    - **Coverage**: Which % of the Regulatory Library is actively covered by current controls.

## UX Rules

- **No Black Boxes**: Never show a "Risk Detected" label without a "View Reasoning" button.
- **Confidence Thresholds**: Visually distinguish between "High Confidence" (AI-pushed) and "Manual Review Required" (Borderline cases).

## Technical Implementation

- **Chain of Thought**: Using LangChain's `self-reflection` patterns.
- **Versioning**: Using a temporal table for `surveillance_controls` to track state changes.

See [Surveillance Controls](./surveillance_controls.md) for enforcement logic.
