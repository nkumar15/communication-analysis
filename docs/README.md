# Multi-Tenant SaaS Accelerator Documentation

## 1. System Documentation
- **[Architecture](architecture/README.md)**: High-level design, Security, Isolation.
- **[Standards](standards/README.md)**: UI Design, Code Style, Policy.
- **[Guides](guides/README.md)**: Deployment, Data Management, How-tos.
- **[Specifications](specifications/)**: Product Requirements (PRDs).

## 2. Feature Index
This index links to technical documentation co-located with the source code.

### Foundation Layers
- [B2B Core (Auth, Billing, Users)](../backend/modules/b2b/README.md)
- [B2C Core (Auth, Workspaces)](../backend/modules/b2c/README.md)
- [Platform (Super-Admin)](../backend/modules/platform/README.md)

### B2B Domain
- [Task Management (Projects, Tasks)](../backend/modules/domains/b2b/task_management/README.md)
- [Bank Surveillance (Enron)](../backend/modules/domains/b2b/bank_surveillance/README.md)

### B2C Domain
- [Finance Trader (RAG)](../backend/modules/domains/b2c/finance_trader/README.md)

## 3. Operations
- [Environment Setup Runbook](operations/environment-setup.md) — local dev, domain enablement, production checklist

## 4. Developer Guides
- [Setup Guide](../README.md)
