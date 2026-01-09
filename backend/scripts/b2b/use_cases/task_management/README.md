# Task Management Use Case (Default)

Complete RBAC configuration for Project/Task Management SaaS.

## Features

- **Teams = Project teams**
- **Resources:** projects, tasks, comments, rag_documents
- **Simple:** Uses base roles (owner/admin/member) with task permissions

## Usage

```bash
# Load this use case
USE_CASE=task_management python scripts/b2b/seed_rbac.py

# To customize for production
cp -r use_cases/task_management/* domain/
# Edit domain/ files as needed
python scripts/b2b/seed_rbac.py
```
