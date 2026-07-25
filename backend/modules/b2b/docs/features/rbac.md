# Role-Based Access Control (RBAC)

> **Status**: ![Status](https://img.shields.io/badge/Status-Complete-green)

A powerful 3-Layer permission model for fine-grained access control.

## Quick Reference
- [Technical Spec](../technical/rbac.md)
- [Roles Page](../pages/team_members.md)

## Overview
Ensures users can only access data permitted by their role and context.
- **System Roles**: Billing/Admin access (e.g., Owner, Member).
- **Business Roles**: Functional access (e.g., Analyst, Reviewer).
- **Plugin Constraints**: Geo-fencing and Data Classification.

## Workflows

### 1. Permission Check
**Trigger**: API Request to protected endpoint.
**Process**:
1.  Middleware authenticates user.
2.  RBAC Service enriches user context (Geo, Level).
3.  Plugins run Pre-Check (fast deny).
4.  Core RBAC checks table permissions.
5.  Plugins run Post-Check (deep verify).
**Output**: Allow (200) or Deny (403).

### 2. Assigning Roles
**Trigger**: Owner updates a user's role.
**Process**: Updates `team_members` or `users` table. cache invalidation.
**Output**: User has new permissions immediately.

## Implementation Checklist
- [x] 3-Layer Model (System, Business, Plugin)
- [x] `RBACService` with Plugin interceptors
- [x] Middleware integration
- [x] Standard Plugin Set (Geo, Hierarchy)

## Design Decisions
| Decision | Rationale |
| :--- | :--- |
| **Plugin Architecture** | Allows extending logic (e.g., Geo-fencing) without modifying core code. |
| **Context Enrichment** | Gathers all necessary data (Region, Clearance) upfront for efficient checks. |
| **Deny-by-Default** | Safest security posture; requires explicit grant. |
