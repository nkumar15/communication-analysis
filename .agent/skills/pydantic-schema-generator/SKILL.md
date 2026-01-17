name: pydantic-schema-generator
description: Generate Pydantic schemas from SQLAlchemy models.

# Instructions

When asked to "generate schemas" for a model, follow these steps:

1.  **Analyze the Model**
    - Identify columns and types.
    - Identify required vs optional fields (nullable).
    - Identify relationships (should they be included?).

2.  **Generate Schemas**
    - **Base Schema**: Shared fields (usually matches DB columns).
    - **Create Schema**: Fields required for creation (exclude ID, timestamps, computed fields).
    - **Update Schema**: All fields optional (for PATCH).
    - **Response Schema**: Full representation including ID and timestamps. Use `model_config = ConfigDict(from_attributes=True)`.

3.  **Boilerplate Template**
    ```python
    from pydantic import BaseModel, ConfigDict, Field, EmailStr
    from typing import Optional, List
    from uuid import UUID
    from datetime import datetime

    class ResourceBase(BaseModel):
        name: str = Field(..., min_length=1, max_length=100)
        description: Optional[str] = None

    class ResourceCreate(ResourceBase):
        pass

    class ResourceUpdate(ResourceBase):
        name: Optional[str] = Field(None, min_length=1)  # Make optional for update

    class ResourceResponse(ResourceBase):
        id: UUID
        tenant_id: UUID
        created_at: datetime
        updated_at: datetime

        model_config = ConfigDict(from_attributes=True)
    ```
