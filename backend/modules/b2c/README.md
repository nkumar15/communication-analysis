# B2C Foundation Module

## 1. Overview
The B2C Foundation module provides the core capabilities for Single-User and Team Workspace SaaS applications. It handles user authentication, personal/team workspaces, and subscription billing.

## 2. Architecture
This module follows a **Layered Architecture**:
- `routers/`: API endpoints
- `services/`: Business logic
- `models/`: Database entities
- `schemas/`: Pydantic models (DTOs)

## 3. Feature Documentation
Detailed technical documentation for each foundation feature can be found below:

### Core Identity & Access
- [Authentication](docs/auth.md)

### Workspace Management
- [Workspaces & Members](docs/workspaces.md)

### Commercialization
- [Billing & Subscriptions](docs/billing.md)

## 4. Dependencies
- **Core**: `services.authentication`, `db.session`
- **External**: Stripe (Billing), Firebase (Auth)
