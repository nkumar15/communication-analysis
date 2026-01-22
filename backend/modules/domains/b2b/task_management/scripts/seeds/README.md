# Task Management Use Case (Default)

Complete RBAC configuration for Project/Task Management SaaS.

## Features

- **Teams = Project teams**
- **Resources:** projects, tasks, comments, rag_documents
- **Simple:** Uses base roles (owner/admin/member) with task permissions

## Usage
```bash
# 1. Reset DB and seed RBAC with task management use case
make reset-db
make b2b-seed-roles USE_CASE=task_management

# 2. Create demo tenant
make b2b-invite f=scripts/b2b/use_cases/task_management/task_management_demo.json

# 3. Demo is ready!
# - Domain: firstcompany.net
```

## Demo Configuration

**Fixed Tenant ID:** `05b51fa4-45f4-50c2-a3f4-4c122000347b`
- Ensures idempotency
- Default fallback for `make b2b-invite`

**Primary Persona:**
- **Role:** Generic Owner
- **Context:** Standard project/task management SaaS
