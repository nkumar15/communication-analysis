---
name: pydantic-schema-generator
description: Generate Pydantic v2 schemas from SQLAlchemy models following project conventions.
---

# Pydantic Schema Generator

Generate Pydantic v2 DTOs (Data Transfer Objects) from SQLAlchemy ORM models.

## When To Use

**Trigger Phrases:**
- "Generate schemas for [Model]"
- "Create DTOs for [endpoint]"
- "Add request/response schemas for [resource]"

**Auto-invoked when:**
- A new endpoint is being added (after model is confirmed)
- A DB migration adds/removes columns that affect the API surface

**Do NOT invoke when:**
- Only fixing business logic with no schema change
- Refactoring service internals only

---

## 1. Schema Set — One Model, Four Schemas

Every resource needs four schemas. Use this naming convention without exception:

| Schema | Purpose | Excludes |
|--------|---------|---------|
| `ResourceBase` | Shared writable fields | `id`, `tenant_id`, timestamps, computed fields |
| `ResourceCreate(ResourceBase)` | POST body | (inherits Base, adds tenant_id if needed) |
| `ResourceUpdate(BaseModel)` | PATCH body — all fields Optional | (standalone, not inheriting Base) |
| `ResourceResponse(ResourceBase)` | API response | (adds id, tenant_id, timestamps; `from_attributes=True`) |

> **Rule**: `ResourceUpdate` does NOT inherit `ResourceBase` — Base has required fields, Update must make everything optional.

---

## 2. Boilerplate Template

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ResourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ResourceCreate(ResourceBase):
    tenant_id: UUID  # only if caller supplies tenant; omit if inferred from token


class ResourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class ResourceResponse(ResourceBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## 3. Common Patterns

### Enums
```python
from enum import Enum

class StatusEnum(str, Enum):
    active = "active"
    suspended = "suspended"
    pending = "pending"

class ResourceBase(BaseModel):
    status: StatusEnum = StatusEnum.active
```

### Field Aliases (e.g., reserved Python names like `metadata`)
```python
from pydantic import Field, AliasChoices

class ResourceBase(BaseModel):
    metadata_: dict = Field(
        default={},
        validation_alias=AliasChoices("metadata_", "metadata"),
        serialization_alias="metadata",
    )
```

### Nested / Relationship Schemas
Only include relationships in `Response` schemas, not in `Create`/`Update`:
```python
class TeamSummary(BaseModel):
    id: UUID
    name: str
    model_config = ConfigDict(from_attributes=True)

class ResourceResponse(ResourceBase):
    id: UUID
    team: Optional[TeamSummary] = None  # populated via selectinload in service
    model_config = ConfigDict(from_attributes=True)
```

### Validators
```python
from pydantic import field_validator

class ResourceCreate(ResourceBase):
    email: str

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()
```

### JSONB / Dict columns
```python
from typing import Any, Dict

class ResourceBase(BaseModel):
    config: Dict[str, Any] = {}
    tags: List[str] = []
```

### Pagination wrapper (list responses)
```python
class ResourceListResponse(BaseModel):
    items: List[ResourceResponse]
    total: int
    limit: int
    offset: int
```

---

## 4. File Placement

```
modules/{b2b,b2c,platform}/schemas/
└── resource.py          # EntityCreate, EntityUpdate, EntityResponse

modules/domains/b2b/{domain}/schemas/
└── resource.py
```

One file per resource. Do not mix unrelated schemas in a single file.

---

## 5. Checklist Before Delivery

- [ ] All four schemas present: `Base`, `Create`, `Update`, `Response`
- [ ] `Update` inherits `BaseModel` directly (not `Base`) — all fields Optional
- [ ] `Response` has `model_config = ConfigDict(from_attributes=True)`
- [ ] No ORM objects in schemas — only primitives, UUIDs, datetimes, nested Pydantic models
- [ ] Enums are `str, Enum` (JSON-serializable)
- [ ] Reserved names aliased (`metadata` → `metadata_` with `AliasChoices`)
- [ ] Relationships only in `Response`, never in `Create`/`Update`
- [ ] Nested response schemas also have `from_attributes=True`
