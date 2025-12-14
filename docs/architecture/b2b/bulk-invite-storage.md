# Bulk Invite File Storage & Download Strategy

## Summary

**✅ CSV Upload**: Parse in memory, **do NOT store** on disk  
**✅ Results Storage**: Store in PostgreSQL database (`bulk_invite_jobs` table)  
**✅ Downloads**: Generate CSV files on-demand from database

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         UPLOAD FLOW                              │
└─────────────────────────────────────────────────────────────────┘

1. User uploads CSV (2MB max)
   ↓
2. FastAPI UploadFile (in-memory if <2MB)
   ↓
3. Parse CSV rows
   ↓
4. Validate all rows
   ↓
5. Create invitation records in DB
   ↓
6. Store job results in bulk_invite_jobs table (JSONB)
   ↓
7. Discard original CSV ← NOT STORED!
   ↓
8. Return job_id and results to user


┌─────────────────────────────────────────────────────────────────┐
│                        DOWNLOAD FLOW                             │
└─────────────────────────────────────────────────────────────────┘

1. User clicks "Download Results"
   ↓
2. GET /api/b2b/invitations/bulk/{job_id}/download
   ↓
3. Query bulk_invite_jobs table (JSONB)
   ↓
4. Generate CSV in memory
   ↓
5. Stream CSV to user
   ↓
6. No file stored on server!
```

---

## Database Schema

```sql
CREATE TABLE b2b.bulk_invite_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES b2b.tenants(id),
    created_by UUID NOT NULL REFERENCES b2b.users(id),
    total_rows INT NOT NULL,
    successful_count INT NOT NULL,
    failed_count INT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bulk_invite_jobs_tenant 
    ON b2b.bulk_invite_jobs(tenant_id, created_at DESC);
```

---

## Download Endpoints

### 1. Download All Results

```http
GET /api/b2b/invitations/bulk/{job_id}/download
Authorization: Bearer {token}
```

**Response Headers**:
```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="bulk_invite_results_2025-12-13.csv"
```

**Response Body** (CSV):
```csv
row,email,name,role,team_name,status,invitation_id,error
1,alice@acme.com,Alice Smith,admin,Engineering,success,uuid-123,
2,bob@acme.com,Bob Jones,member,Sales,success,uuid-456,
3,invalid@wrong.com,,,error,,Email domain mismatch
```

### 2. Download Failures Only

```http
GET /api/b2b/invitations/bulk/{job_id}/download/failures
Authorization: Bearer {token}
```

**Response Body** (CSV - only failed rows):
```csv
row,email,name,role,team_name,error
3,invalid@wrong.com,,,Email domain must match tenant domain (acme.com)
5,duplicate@acme.com,,,User already exists in tenant
7,bob@wrongdomain.com,,,Email domain must match tenant domain (acme.com)
```

**Use Case**: User fixes errors and re-uploads this CSV

### 3. Download Template

```http
GET /api/b2b/invitations/bulk/template
```

**Response Body** (CSV template):
```csv
email,role,team_name,team_role,name
# Format: email@domain.com,role,team_name,team_role,Display Name
# Required: email, role
# Optional: team_name, team_role, name
# Valid roles: owner, admin, member, viewer
# Valid team_roles: team_manager, team_contributor, team_reader
alice@yourdomain.com,admin,Engineering,team_manager,Alice Smith
bob@yourdomain.com,member,Engineering,team_contributor,Bob Jones
carol@yourdomain.com,viewer,Sales,team_reader,Carol White
```

---

## Implementation

### Endpoint Implementation

```python
# services/b2b/routers/invitations.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from io import StringIO
import csv
from datetime import datetime

router = APIRouter()

@router.get("/invitations/bulk/{job_id}/download")
async def download_bulk_results(
    job_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download full bulk invite results as CSV"""
    
    # Fetch job
    job = await db.execute(
        select(BulkInviteJob).where(
            BulkInviteJob.id == job_id,
            BulkInviteJob.tenant_id == current_user['tenant_id']
        )
    )
    job = job.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Generate CSV in memory
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['row', 'email', 'name', 'role', 'team_name', 
                   'status', 'invitation_id', 'error']
    )
    writer.writeheader()
    
    for row_data in job.results['rows']:
        writer.writerow(row_data)
    
    # Return as streaming response
    output.seek(0)
    filename = f"bulk_invite_results_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/invitations/bulk/{job_id}/download/failures")
async def download_failures(
    job_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download only failed rows for correction"""
    
    # Fetch job
    job = await get_bulk_job(db, job_id, current_user['tenant_id'])
    
    # Filter only failures
    failures = [
        row for row in job.results['rows'] 
        if row['status'] == 'error'
    ]
    
    # Generate CSV
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['row', 'email', 'name', 'role', 'team_name', 'error']
    )
    writer.writeheader()
    
    for row in failures:
        writer.writerow({
            'row': row['row'],
            'email': row.get('email', ''),
            'name': row.get('name', ''),
            'role': row.get('role', ''),
            'team_name': row.get('team_name', ''),
            'error': row.get('error', '')
        })
    
    output.seek(0)
    filename = f"bulk_invite_failures_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/invitations/bulk/template")
async def download_template():
    """Download CSV template"""
    
    template = """email,role,team_name,team_role,name
# Example rows:
alice@yourdomain.com,admin,Engineering,team_manager,Alice Smith
bob@yourdomain.com,member,Engineering,team_contributor,Bob Jones
carol@yourdomain.com,viewer,Sales,team_reader,Carol White
"""
    
    return StreamingResponse(
        iter([template]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="bulk_invite_template.csv"'
        }
    )
```

---

## Benefits

### ✅ No File Storage Needed
- No S3/GCS/local filesystem complexity
- No tenant isolation concerns for files
- No cleanup jobs for old files

### ✅ Database-Centric
- Results queryable via SQL
- Easy to add filtering/search
- Audit trail built-in
- JSONB provides flexibility

### ✅ Privacy-Friendly
- Original CSV not retained
- Only processed results stored
- User can delete job results

### ✅ Scalable
- JSONB handles up to ~100 rows easily
- Can paginate job list
- Download generation is fast (in-memory)

---

## UI Flow

### Upload Page

```
┌─────────────────────────────────────────────┐
│  Bulk Invite Users                          │
├─────────────────────────────────────────────┤
│                                             │
│  [Download Template] ← Get CSV template     │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  Drag & Drop CSV or Click to Browse  │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  [ Upload & Process ]                       │
└─────────────────────────────────────────────┘
```

### Results Page

```
┌─────────────────────────────────────────────┐
│  Bulk Invite Results                        │
├─────────────────────────────────────────────┤
│  ✅ 8 invitations sent                      │
│  ⚠️  2 failed                                │
│                                             │
│  [Download All Results]                     │
│  [Download Failures Only] ← Fix & re-upload│
│                                             │
│  Detailed Results:                          │
│  ┌───┬──────────────┬────────┬─────────┐   │
│  │ # │ Email        │ Status │ Error   │   │
│  ├───┼──────────────┼────────┼─────────┤   │
│  │ 1 │ alice@...    │ ✅      │         │   │
│  │ 2 │ bob@...      │ ✅      │         │   │
│  │ 3 │ invalid@...  │ ❌      │ Domain  │   │
│  └───┴──────────────┴────────┴─────────┘   │
└─────────────────────────────────────────────┘
```

---

## Key Points

1. **CSV never touches disk** - all in-memory processing
2. **Results in database** - query, filter, audit
3. **Downloads on-demand** - generated from database
4. **Tenant isolation** - via tenant_id in database
5. **No cleanup needed** - old jobs just age out in DB
