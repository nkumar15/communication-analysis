# Bank Surveillance (Worldwide Bank)

> An enterprise-grade surveillance platform for a Global Systemically Important Bank (G-SIB).

## Overview

The Bank Surveillance workbench balances **Global Risk Oversight** with strict **Data Sovereignty** and **Information Security**. It empowers compliance officers to detect financial misconduct (Insider Trading, Collusion) using AI agents and network analysis, while enforcing "Chinese Walls" and "Need-to-Know" access controls.

**Key Enterprise Constraints:**
*   **Geo-Fencing**: Data must remain within its jurisdiction (e.g., Singapore data stays in SG). Only "Global" roles can bridge these silos.
*   **Information Barriers**: Investment Banking data must remain invisible to Public Side employees.
*   **Clearance**: Sensitive data (e.g., Whistleblower Tips) is redacted for unauthorized users.

## Target Platform
- [x] Web
- [ ] Mobile (iOS/Android)
- [ ] Backend API Only

## User Stories

<!-- High-Level Product Goals & Epics -->

### Global Command & Control
1.  **As the Global CSO**, I want to aggregate risk alerts across regions so that I can see the institution's total risk posture.
2.  **As the Global CSO**, I want to "drill down" into the Singapore desk's data so that I can investigate cross-border collusion that a local analyst creates.
3.  **As a Regional Director**, I want to investigate cross-border collusion while respecting local data privacy laws.

### Advanced Investigation
1.  **As a Senior Analyst**, I want AI to explain *why* an alert triggered (contextual reasoning) rather than just flagging keywords.
2.  **As an Ops Maker**, I want to prepare a high-risk case for review so that a "Checker" can approve it (4-Eyes Principle).
3.  **As an Analyst**, I want to visualize the "Social Graph" to find hidden cliques and communication patterns.

### Fortified Security (Internal Threat)
1.  **As a Junior Analyst**, I should see **[REDACTED]** content when viewing a "Top Secret" alert so that I am not exposed to material non-public information (MNPI).
2.  **As an IT Admin**, I want to assign users to specific "Regions" so that they physically cannot access foreign data.

### Regulatory Governance
1.  **As an External Auditor**, I want read-only access to "Chain of Custody" logs without seeing raw message content.
2.  **As a Risk Officer**, I want to configure different retention policies for US vs EU regions.

### Operations & Data Management
1.  **As a Compliance Ops Officer**, I want the system to automatically ingest daily email dumps (YYYYMMDD) so that data is immediately available for search and analysis without manual upload.
2.  **As a Data Engineer**, I want the ingestion process to index content for both RAG (vector) and Keyword search so that analysts can find messages using broad concepts or specific terms.

## Documentation

| Document | Description |
|----------|-------------|
| [Personas](./docs/personas.md) | Deep dive into the 11-role ecosystem |
| [Navigation IA](./docs/navigation.md) | Information architecture and page hierarchy |
| [Page Specifications](./docs/pages/) | Per-page specs with user stories and wireframes |
| - [Ingestion](./docs/pages/ingestion.md) | **Daily dump status & stats (New)** |
| - [Dashboard](./docs/pages/dashboard.md) | |
| [Demo Scripts](./docs/demos/README.md) | **Scripted demos for Global, Analyst, and Audit flows** |
| [Technical](./docs/technical/) | API, Schema, Architecture |

## Quick Links

### Product Docs
- [User Personas](./docs/personas.md)
- [RBAC Specification](./docs/technical/architecture.md#rbac-specification)

### Technical Docs
- [API Reference](./docs/technical/api.md)
- [Database Schema](./docs/technical/schema.md)
- [Architecture](./docs/technical/architecture.md)
