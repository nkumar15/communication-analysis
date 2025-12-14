# SPEC-05: Bulk User Invitations

**Status**: Draft / Design  
**Created**: 2025-12-13  
**Owner**: Backend Team

---

## Overview

Enable administrators to invite multiple users simultaneously via CSV file upload, streamlining the onboarding process for teams with many users.

---

## Business Requirements

### User Stories

**As an Admin**, I want to invite multiple users at once so that I can onboard entire teams efficiently.

**As an Admin**, I want to see validation errors before sending invites so that I can correct mistakes.

**As an Admin**, I want to assign different roles and teams to different users in bulk so that I have flexibility in team organization.

### Success Criteria

- ✅ Upload CSV file with up to 100 users at once
- ✅ Validate all entries before processing
- ✅ Show clear error messages for invalid entries
- ✅ Send all valid invitations even if some fail
- ✅ Provide downloadable results with success/failure status

---

## Functional Requirements

### 1. CSV File Format

**Required Columns**:
- `email` - User email address (must match tenant domain)
- `role` - Tenant role (owner, admin, member, viewer)

**Optional Columns**:
- `team_name` - Team to assign user to (creates if doesn't exist)
- `team_role` - Team role (team_manager, team_contributor, team_reader)
- `name` - Display name for the user

**Example CSV**:
```csv
email,role,team_name,team_role,name
alice@acme.com,admin,Engineering,team_manager,Alice Smith
bob@acme.com,member,Engineering,team_contributor,Bob Jones
carol@acme.com,member,Sales,team_contributor,Carol White
dave@acme.com,viewer,Sales,team_reader,Dave Brown
```

**CSV Rules**:
- UTF-8 encoding
- Header row required (case-insensitive)
- Max file size: 2MB
- Max rows: 100 users per upload
- Empty rows ignored
- Whitespace trimmed from all fields

### 2. Validation Rules

**Per-Row Validation**:
- ✅ Email format valid
- ✅ Email domain matches tenant domain
- ✅ Email not already a user in tenant
- ✅ Email not already invited (pending invitation)
- ✅ Role is valid (owner, admin, member, viewer)
- ✅ Team role is valid (if provided)
- ✅ Current user has permission to invite with that role (role hierarchy)

**File-Level Validation**:
- ✅ File is valid CSV format
- ✅ Has required columns (email, role)
- ✅ Does not exceed row limit (100)
- ✅ Does not exceed file size limit (2MB)
- ✅ No duplicate emails within file

**RBAC Validation**:
- Owner can invite anyone with any role
- Admin can invite admin/member/viewer (NOT owner)
- Member/Viewer cannot use bulk invite

### 3. Processing Behavior

**Validation-First Approach**:
1. Upload file
2. Parse and validate ALL rows
3. Return validation errors if any exist
4. User corrects errors and re-uploads
5. Once valid, process all invitations

**Alternative: Partial Processing** (recommended):
1. Upload file
2. Parse and validate ALL rows
3. Separate into valid and invalid rows
4. Process ALL valid rows (send invitations)
5. Return results with:
   - Success count
   - List of successful invitations
   - List of failed rows with error messages

**Error Recovery**:
- Invalid rows do NOT block valid rows
- All valid invitations are sent
- Failed rows can be fixed and re-uploaded

### 4. Team Handling

**If team_name provided**:
- Look up existing team by name (case-insensitive)
- If team doesn't exist:
  - **Option A** (Auto-create): Create team automatically
  - **Option B** (Validation error): Require team to exist first
  - **Recommended**: Option A (auto-create) for better UX

**If team_name empty**:
- Assign to default team
- Use default team role (team_contributor)

**Team Role Assignment**:
- If team_role provided: use it
- If team_role empty: default to team_contributor

### 5. Invitation Process

For each valid row:
1. Create invitation record in database
2. Generate unique invitation token
3. Queue email sending (background task)
4. Record result (success/failure)

**Email Sending**:
- Send emails asynchronously (Celery background tasks)
- Don't fail the entire bulk operation if individual emails fail
- Log email failures for admin review

---

## File Storage Strategy

### CSV Upload Handling

**No File Persistence** - CSV files are NOT stored:
1. CSV uploaded via HTTP multipart
2. Parsed in memory (FastAPI UploadFile)
3. Validated and processed
4. **Discarded after processing**

**Why Not Store:**
- ✅ No storage complexity
- ✅ No tenant isolation concerns for files
- ✅ Privacy-friendly (don't retain uploaded data)
- ✅ Simpler architecture

### What IS Stored

**Database Table**: `bulk_invite_jobs`
```sql
CREATE TABLE b2b.bulk_invite_jobs (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    created_by UUID REFERENCES b2b.users(id),
    total_rows INT NOT NULL,
    successful_count INT NOT NULL,
    failed_count INT NOT NULL,
    results JSONB NOT NULL,  -- Detailed per-row results
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Results JSONB Structure**:
```json
{
  "rows": [
    {
      "row": 1,
      "email": "alice@acme.com",
      "name": "Alice Smith",
      "role": "admin",
      "team_name": "Engineering",
      "status": "success",
      "invitation_id": "uuid-123"
    },
    {
      "row": 3,
      "email": "invalid@wrong.com",
      "status": "error",
      "error": "Email domain must match tenant domain (acme.com)"
    }
  ]
}
```

### Download Options

**1. Download Results** (all rows):
- Endpoint: `GET /api/b2b/invitations/bulk/{job_id}/download`
- Returns: CSV with all results (success + failures)

**2. Download Failures Only**:
- Endpoint: `GET /api/b2b/invitations/bulk/{job_id}/download/failures`
- Returns: CSV with only failed rows + error messages
- Use case: Fix errors and re-upload

**3. Download Template**:
- Endpoint: `GET /api/b2b/invitations/bulk/template`
- Returns: CSV template with headers + example rows

---

## API Design

### Endpoints

#### 1. Upload & Process Bulk Invites

```
POST /api/b2b/invitations/bulk
Content-Type: multipart/form-data
```

**Request**:
```
{
  "file": <CSV file>,
  "send_emails": true,  // Optional, default true
  "auto_create_teams": true  // Optional, default true
}
```

**Response (Success)**:
```json
{
  "job_id": "uuid-abc123",
  "total_processed": 10,
  "successful": 8,
  "failed": 2,
  "results": [
    {
      "row": 1,
      "email": "alice@acme.com",
      "status": "success",
      "invitation_id": "uuid-123"
    },
    {
      "row": 3,
      "email": "invalid@wrong.com",
      "status": "error",
      "error": "Email domain must match tenant domain (acme.com)"
    }
  ],
  "teams_created": ["Sales", "Marketing"],
  "download_url": "/api/b2b/invitations/bulk/uuid-abc123/download",
  "failures_url": "/api/b2b/invitations/bulk/uuid-abc123/download/failures"
}
```

**Response (Validation Errors)**:
```json
{
  "error": "validation_failed",
  "message": "CSV validation failed",
  "errors": [
    {
      "row": 1,
      "field": "email",
      "message": "Invalid email format"
    },
    {
      "row": 5,
      "field": "role",
      "message": "Invalid role 'superadmin'. Must be one of: owner, admin, member, viewer"
    }
  ]
}
```

#### 2. Download Full Results

```
GET /api/b2b/invitations/bulk/{job_id}/download
```

**Response**: CSV file
```csv
row,email,name,role,team_name,status,invitation_id,error
1,alice@acme.com,Alice Smith,admin,Engineering,success,uuid-123,
2,bob@acme.com,Bob Jones,member,Engineering,success,uuid-456,
3,invalid@wrong.com,,,error,,Email domain must match tenant domain
```

**Headers**:
```
Content-Type: text/csv
Content-Disposition: attachment; filename="bulk_invite_results_2025-12-13.csv"
```

#### 3. Download Failed Rows Only

```
GET /api/b2b/invitations/bulk/{job_id}/download/failures
```

**Response**: CSV file (only failed rows)
```csv
row,email,name,role,team_name,error
3,invalid@wrong.com,,,Email domain must match tenant domain
5,duplicate@acme.com,,,User already exists in tenant
```

**Use Case**: User can fix errors and re-upload this CSV

#### 4. Download CSV Template

```
GET /api/b2b/invitations/bulk/template
```

**Response**: CSV template
```csv
email,role,team_name,team_role,name
alice@yourdomain.com,admin,Engineering,team_manager,Alice Smith
bob@yourdomain.com,member,Engineering,team_contributor,Bob Jones
```

#### 5. Get Job Status

```
GET /api/b2b/invitations/bulk/{job_id}
```

**Response**:
```json
{
  "job_id": "uuid-abc123",
  "status": "completed",
  "total_rows": 10,
  "successful": 8,
  "failed": 2,
  "created_at": "2025-12-13T20:30:00Z",
  "created_by": {
    "id": "user-uuid",
    "email": "admin@acme.com"
  },
  "download_url": "/api/b2b/invitations/bulk/uuid-abc123/download"
}
```

#### 6. List Bulk Invite Jobs

```
GET /api/b2b/invitations/bulk/jobs
```

**Response**:
```json
{
  "jobs": [
    {
      "job_id": "uuid-abc123",
      "total_rows": 10,
      "successful": 8,
      "failed": 2,
      "created_at": "2025-12-13T20:30:00Z",
      "created_by": "admin@acme.com"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

### Permissions

**Required Permission**: `users:invite`

**Roles Allowed**:
- Owner: ✅
- Admin: ✅
- Member: ❌
- Viewer: ❌

---

## UI Design

### Upload Component

**Location**: `/invitations` page

**UI Flow**:
1. **Upload Button**: "Bulk Invite Users" button
2. **Modal/Page**: Opens bulk invite interface
3. **File Picker**: Drag-drop or file browser
4. **Template Download**: Link to download CSV template
5. **Validation Feedback**: Show errors immediately after upload
6. **Preview Table**: Show parsed data (first 10 rows)
7. **Confirm Button**: "Send Invitations" button
8. **Results Display**: Success/failure summary with downloadable report

**CSV Template**:
Provide downloadable template with:
- Header row
- Example rows (commented or instructional)
- Column descriptions

```csv
email,role,team_name,team_role,name
# Example: user@yourdomain.com,member,Engineering,team_contributor,John Doe
alice@yourdomain.com,admin,Engineering,team_manager,Alice Smith
bob@yourdomain.com,member,Engineering,team_contributor,Bob Jones
```

### Error Display

**File-Level Errors** (shown immediately):
- "File too large (max 2MB)"
- "Invalid CSV format"
- "Too many rows (max 100)"

**Row-Level Errors** (shown in table):
- Highlight invalid rows in red
- Show error message next to field
- Allow download of errors as CSV for correction

### Results Display

**Success Summary**:
```
✅ Successfully invited 8 users
⚠️ 2 invitations failed
📧 Invitation emails queued for sending
```

**Detailed Results Table**:
| Row | Email | Name | Status | Details |
|-----|-------|------|--------|---------|
| 1 | alice@acme.com | Alice Smith | ✅ Success | Invited as Admin |
| 2 | bob@acme.com | Bob Jones | ✅ Success | Invited as Member |
| 3 | invalid@wrong.com | - | ❌ Failed | Domain mismatch |

**Download Options**:
- Download successful invitations (CSV)
- Download failed rows for correction (CSV)
- Download full results report (CSV)

---

## Technical Implementation

### Backend Components

**1. CSV Parser Service**
```python
# services/b2b/utils/csv_parser.py
class BulkInviteCSVParser:
    def parse_file(file) -> List[InviteRow]
    def validate_rows(rows) -> ValidationResult
```

**2. Bulk Invite Endpoint**
```python
# services/b2b/routers/invitations.py
@router.post("/invitations/bulk")
async def bulk_invite_users(
    file: UploadFile,
    send_emails: bool = True,
    auto_create_teams: bool = True,
    background_tasks: BackgroundTasks,
    current_user: dict = require_permission('users', 'invite'),
    db: AsyncSession = Depends(get_db)
):
    # 1. Parse CSV
    # 2. Validate all rows
    # 3. Create all invitation records (synchronous)
    # 4. Queue email sending (background with NEW session)
    # 5. Return results immediately
```

**3. Invitation Service Update**
```python
# services/b2b/services/invitation_service.py
class InvitationService:
    async def bulk_create_invitations(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        invites: List[BulkInviteRequest],
        inviter_id: UUID,
        auto_create_teams: bool = True
    ) -> BulkInviteResult:
        """Create all invitation records synchronously"""
        # This runs in the main request transaction
        # Returns list of created invitations
```

**4. Background Email Sending - CRITICAL SOLUTION**

**Problem**: FastAPI BackgroundTasks share the same DB session, causing:
- Database lock issues
- Session closure errors
- Transaction conflicts

**Solution**: Create a NEW database session in the background task

```python
# services/b2b/tasks/email_tasks.py
from core.database import AsyncSessionLocal

async def send_bulk_invitation_emails(
    invitation_ids: List[UUID],
    tenant_id: UUID
):
    """
    Send invitation emails in background with NEW database session.
    
    IMPORTANT: This creates its own DB session to avoid lock issues.
    """
    # Create NEW session for background task
    async with AsyncSessionLocal() as db:
        try:
            # Fetch invitations with the new session
            invitations = await _fetch_invitations(db, invitation_ids)
            
            # Send emails (external service, no DB needed)
            for invitation in invitations:
                try:
                    await email_service.send_invitation_email(
                        to_email=invitation.email,
                        invitation_token=invitation.invitation_token,
                        tenant_name=invitation.tenant.name,
                        expires_at=invitation.expires_at
                    )
                    
                    # Update invitation status (optional)
                    invitation.email_sent_at = datetime.utcnow()
                    
                except Exception as e:
                    # Log email failure but continue with others
                    logger.error(f"Failed to send invitation to {invitation.email}: {e}")
            
            # Commit email status updates
            await db.commit()
            
        except Exception as e:
            logger.error(f"Bulk email task failed: {e}")
            await db.rollback()
        finally:
            await db.close()


async def _fetch_invitations(db: AsyncSession, invitation_ids: List[UUID]):
    """Fetch invitations with related tenant data"""
    result = await db.execute(
        select(InvitationModel)
        .options(selectinload(InvitationModel.tenant))
        .where(InvitationModel.id.in_(invitation_ids))
    )
    return result.scalars().all()
```

**5. Endpoint Implementation**

```python
@router.post("/invitations/bulk")
async def bulk_invite_users(
    file: UploadFile,
    send_emails: bool = True,
    background_tasks: BackgroundTasks,
    current_user: dict = require_permission('users', 'invite'),
    db: AsyncSession = Depends(get_db)
):
    # Parse and validate CSV
    parser = BulkInviteCSVParser()
    rows = await parser.parse_file(file)
    validation_result = await parser.validate_rows(
        rows, 
        current_user, 
        db
    )
    
    if validation_result.has_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_failed",
                "errors": validation_result.errors
            }
        )
    
    # Create all invitations in THIS request's transaction
    result = await invitation_service.bulk_create_invitations(
        db=db,
        tenant_id=current_user['tenant_id'],
        invites=rows,
        inviter_id=current_user['id'],
        auto_create_teams=True
    )
    
    # Commit invitation records NOW (before response)
    await db.commit()
    
    # Queue email sending with NEW session (background)
    if send_emails and result.successful_ids:
        background_tasks.add_task(
            send_bulk_invitation_emails,
            invitation_ids=result.successful_ids,
            tenant_id=current_user['tenant_id']
        )
    
    # Return results immediately (emails send in background)
    return {
        "total_processed": result.total,
        "successful": result.successful_count,
        "failed": result.failed_count,
        "results": result.details,
        "teams_created": result.teams_created
    }
```

**6. Alternative: Task Queue (Future Enhancement)**

For production scale, consider a proper task queue:

```python
# Using Celery or ARQ
from app.tasks import celery_app

@celery_app.task
def send_invitation_email_task(invitation_id: str):
    """Celery task with its own DB connection"""
    # Celery manages DB sessions automatically
    # More robust retry logic
    # Better monitoring and failure handling
```

**Why This Works**:
- ✅ Main request creates invitations and commits
- ✅ Background task gets NEW session (no locks)
- ✅ Email failures don't block invitation creation
- ✅ User gets immediate response
- ✅ Emails sent asynchronously

### Database Session Management Strategy

**Main Request Flow**:
```python
async with AsyncSession(engine) as db:  # Request session
    # 1. Parse CSV
    # 2. Validate rows
    # 3. Create invitations
    # 4. Create teams
    await db.commit()  # Commit before response
    # 5. Return response
    
# Background task starts AFTER response sent
```

**Background Task Flow**:
```python
async with AsyncSessionLocal() as db:  # NEW session
    # 1. Fetch invitation data
    # 2. Send emails
    # 3. Update email_sent_at
    await db.commit()
    await db.close()
```

**Key Points**:
- Background task creates its own session
- No shared session = No lock issues
- Main request commits before background starts
- Background task is independent

### Frontend Components

**1. BulkInviteModal Component**
```jsx
// components/invitations/BulkInviteModal.jsx
- File uploader
- CSV validator (client-side)
- Results display
```

**2. CSV Template Generator**
```jsx
// utils/csvTemplate.js
export const generateInviteTemplate = () => {
  // Generate CSV template for download
}
```

**3. Results Table Component**
```jsx
// components/invitations/BulkInviteResults.jsx
- Show success/failure
- Download results
```

---

## Security Considerations

### Input Validation
- ✅ File size limit (2MB)
- ✅ Row count limit (100)
- ✅ Email format validation
- ✅ Domain verification
- ✅ Role validation against hierarchy

### RBAC Enforcement
- ✅ Check `users:invite` permission
- ✅ Enforce role hierarchy (admin cannot invite owner)
- ✅ Verify tenant isolation

### Rate Limiting
- ✅ Limit bulk invites per user (e.g., 5 per hour)
- ✅ Limit total invitations per tenant (e.g., 1000 pending max)

### Audit Trail
- ✅ Log all bulk invite operations
- ✅ Record who invited whom
- ✅ Track source (single vs bulk)

---

## Error Handling

### Common Errors

| Error | HTTP Code | Message | User Action |
|-------|-----------|---------|-------------|
| File too large | 413 | File exceeds 2MB limit | Split into smaller files |
| Invalid CSV | 400 | Invalid CSV format | Check file encoding (UTF-8) |
| Too many rows | 400 | Maximum 100 users per upload | Split into multiple uploads |
| Duplicate email in file | 400 | Email appears multiple times in file | Remove duplicates |
| Domain mismatch | 400 | Email domain must match tenant domain | Correct email addresses |
| User already exists | 400 | User already exists in tenant | Remove from CSV |
| Already invited | 400 | Invitation already sent | Remove from CSV |
| Invalid role | 400 | Invalid role name | Use: owner, admin, member, viewer |
| Permission denied | 403 | Cannot invite users with owner role | Admin cannot invite owners |

### Partial Failure Handling

**Strategy**: Process all valid rows, return detailed results

**Example**:
- Upload 10 users
- 2 have invalid emails
- 8 are processed successfully
- Return success for 8, errors for 2
- User can download failed rows, correct, and re-upload

---

## Performance Considerations

### Limits
- Max file size: 2MB (~5000 rows worst case)
- Recommended limit: 100 rows per upload
- Reasoning: Balance between UX and server load

### Optimization
- Parse CSV in chunks for large files
- Use database transactions for atomicity
- Queue email sending (don't wait for SMTP)
- Consider bulk INSERT for invitations table

### Monitoring
- Track average processing time
- Monitor email queue depth
- Alert on high failure rates

---

## Future Enhancements

### Phase 2
- [ ] Excel file support (.xlsx)
- [ ] Drag-and-drop column mapping (flexible CSV format)
- [ ] Bulk update existing invitations
- [ ] Schedule invitations (send later)

### Phase 3
- [ ] Integration with HR systems (Workday, BambooHR)
- [ ] Webhook notifications for bulk operations
- [ ] Bulk invite via API (non-UI)
- [ ] Template library (save common invite patterns)

---

## Open Questions

1. **Team Creation**: Auto-create teams or require pre-existence?
   - **Recommendation**: Auto-create (better UX)

2. **Email Sending**: Synchronous or asynchronous?
   - **Recommendation**: Asynchronous (better performance)

3. **Error Handling**: Stop on first error or process all?
   - **Recommendation**: Process all, return detailed results

4. **Row Limit**: 100, 500, or 1000?
   - **Recommendation**: 100 (balances UX and performance)

5. **Rate Limiting**: Per user or per tenant?
   - **Recommendation**: Both (5/hour per user, 1000 pending per tenant)

---

## Acceptance Criteria

### Must Have
- ✅ Upload CSV with required columns (email, role)
- ✅ Validate all rows before processing
- ✅ Send invitations for valid rows
- ✅ Return detailed success/failure results
- ✅ Download results as CSV
- ✅ Respect RBAC rules (role hierarchy)
- ✅ Match email domain to tenant

### Should Have
- ✅ Support optional team assignment
- ✅ Auto-create teams if needed
- ✅ Client-side CSV preview
- ✅ Downloadable CSV template
- ✅ Audit logging

### Nice to Have
- Drag-drop file upload
- Real-time progress bar
- Email sending retry mechanism
- Duplicate detection across file and existing invites

---

## Timeline Estimate

- **Design & Specification**: 1 day ✅
- **Backend Implementation**: 2-3 days
  - CSV parser: 0.5 days
  - API endpoint: 1 day
  - Service layer: 1 day
  - Tests: 0.5 days
- **Frontend Implementation**: 2-3 days
  - Upload component: 1 day
  - Results display: 1 day
  - Tests: 0.5 days
  - Polish: 0.5 days
- **Testing & QA**: 1 day
- **Documentation**: 0.5 days

**Total**: 6-8 days

---

## References

- [SPEC-01: Authentication](./authentication.md)
- [SPEC-03: RBAC](./rbac.md)
- [Architecture: Authorization](../architecture/authorization.md)
