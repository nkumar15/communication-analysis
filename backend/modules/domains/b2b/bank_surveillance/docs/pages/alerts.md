## Alert Generation Logic

To reduce noise and ensure focused reviews, the system aggregates signals using a strict hierarchy:
- **Aggregation**: **1 Alert per [Sender] per [Day] per [Risk Indicator]**.
- **Contextual Evidence**: When viewing an alert, the system displays the **full conversation thread** containing all triggered Risk Signals for that sender, even if only one message was the primary trigger.
- **Incident Trail**: Historical Risk Signals (including low-score incidents) are visible in the user's risk profile for long-term behavioral analysis.

## Features/Widgets

| Feature | Description |
|---------|-------------|
| Alert List | Sortable table with Risk Typology, Indicator, Confidence, and Signal Count. |
| **Signal Evidence** | A list of all specific messages (Risk Signals) that contributed to this Alert. |
| **Indicator Breakdown** | Visual summary of why these signals were grouped (e.g., "5 matches for 'Load Shifting' detected"). |
| **AI Reasoning Sidebar** | **(AI Trust)** A slide-out panel showing the AI's "Chain of Thought" logic for this specific classification. |
| **Regulatory Citation** | **(AI Trust)** Explicit links to specific clauses in the **[Regulatory Library](./regulatory_library.md)** explaining the legal context. |
| **Consensus Badge** | **(AI Trust)** Visual indicator of model agreement (e.g., "3/3 Models Agree") to prove robustness. |
| Risk Type Filter | Filter by **Risk Typology** (e.g., Market Manipulation) or **Risk Indicator** (e.g., Front Running). |


## User Stories

1. **As a Surveillance Analyst**, I want to filter alerts by risk type so that I can focus on my assigned category.
2. **As a Surveillance Analyst**, I want to bulk-close low-confidence alerts so that I can manage my queue efficiently.
3. **As a Surveillance Manager**, I want to see alert aging metrics so that I can ensure SLA compliance.
4. **As a Surveillance Analyst**, I want to escalate alerts with one click so that I can quickly involve senior reviewers.
5. **As a Surveillance Analyst**, I want to convert an alert directly to a case so that I can begin formal investigation.
6. **As a Surveillance Analyst**, I want related risky messages grouped into a single alert so that I don't review 5 separate items for one incident.
7. **As a Surveillance Analyst**, I want to see the full conversational thread so that I understand the context of a flagged message.

## UX Rules

- **Alerts as Business Objects**: Alerts are not raw emails; they are containers of evidence.
- **Explainability First**: Never show a "Risk" flag without an immediately accessible "Why?" reasoning sidebar.
- **Source Highlighting**: Within a message, the system MUST highlight the specific phrases that triggered the Risk Indicator.
- **Model Consensus**: Visually badge alerts that have been verified by multiple models (AI Verify standard).
- **Control Traceability**: Every alert must link back to the exact **[Surveillance Control](./surveillance_controls.md)** version that detected it.
- **Color Coding**: Risk levels (Red/Amber/Green) must be based on "Aggregated Confidence," not just single keyword hits.

## Demo Hook

> Alert examples: "Potential earnings leakage – High confidence", "Abnormal secrecy spike in Executive communications"

## Wireframe

![Alerts Wireframe](../wireframes/alerts.png)

## Technical Implementation

See [API Reference](../technical/api.md#alerts)
