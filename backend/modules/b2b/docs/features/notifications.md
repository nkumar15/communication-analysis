# Emails & Notifications

> **Status**: ![Status](https://img.shields.io/badge/Status-Complete-green)

System for transactional emails and user notifications.

## Quick Reference
- [Invitation Service](../services/invitation_service.py)
- [Tenant Service](../services/tenant_service.py)

## Overview
Handles delivery of transactional messages to users.
- **Providers**: SendGrid (Primary), SMTP (Fallback).
- **Templating**: Jinja2 templates for dynamic content.
- **Queuing**: Background processing for reliability.

## Workflows

### 1. Send Invitation
**Trigger**: Owner invites a new member.
**Process**:
1.  `InvitationService` creates token.
2.  Queues email task.
3.  Worker renders `invitation_email.html`.
4.  Sends via configured provider.
**Output**: Email delivered to user's inbox.

### 2. System Alerts
**Trigger**: Billing failure or Security alert.
**Process**: Immediate high-priority notification to Tenant Admins.

## Implementation Checklist
- [x] SendGrid Integration
- [x] HTML Email Templates (`backend/core/templates`)
- [x] Async Task Queue (Celery)
- [x] Failure Retries

## Design Decisions
| Decision | Rationale |
| :--- | :--- |
| **Async Delivery** | Prevents API blocking during slow SMTP handshakes. |
| **Provider Abstraction** | Allows switching between SendGrid/AWS SES/SMTP without code changes. |

## How to Implement

- [ ] **Define Template**: Add HTML file to `core/templates/emails/`.
- [ ] **Create Task**: Define a Celery task in `tasks/email_tasks.py`.
- [ ] **Trigger**: Call `send_email_task.delay()` from your service.
