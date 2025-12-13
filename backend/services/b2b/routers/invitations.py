"""
Invitations API Router

Handles user invitation creation, validation, and acceptance.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from io import StringIO
import csv
from datetime import datetime

from core.database import get_db
from core.middleware import get_current_user
from services.b2b.middleware import get_current_active_user
from services.b2b.services.invitation_service import invitation_service
from services.b2b.services.tenant_service import tenant_service
from services.b2b.schemas.invitation import (
    InviteUserRequest,
    InviteUserResponse,
    InvitationListResponse
)
from services.b2b.rbac import has_permission
from core.email import email_service
from core.config import settings
from core.rls import rls_service
from services.b2b.utils.csv_parser import BulkInviteCSVParser
from core.tasks.email_tasks import send_bulk_invitation_emails, send_invitation_email
from services.b2b.models import UserModel


router = APIRouter(prefix="/api/b2b/invitations", tags=["invitations"])


@router.post("/invite", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite a new user to the tenant
    
    Permission required: users:invite
    
    Role restrictions:
    - Owner: Can invite Owner, Admin, Viewer
    - Admin: Can invite Admin, Viewer
    - Viewer: Cannot invite (no permission)
    """
    # Check permission
    if not await has_permission(current_user['id'], 'users', 'invite', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to invite users"
        )
    
    # Create invitation via service
    invitation, invitation_token = await invitation_service.invite_user_to_tenant(
        db=db,
        tenant_id=current_user['tenant_id'],
        email=request.email,
        role=request.role,
        invited_by_user_id=current_user['id'],
        current_user_role=current_user.get('role'),
        team_id=request.team_id,
        team_role=request.team_role
    )
    
    # Get tenant for email
    tenant = await tenant_service.get_tenant_by_id(db, current_user['tenant_id'])
    
    # Send invitation email via Celery (async)
    send_invitation_email.delay(
        invitation_id=str(invitation.id),
        tenant_id=str(current_user['tenant_id'])
    )
    
    # Log audit event (async via Celery)
    from core.tasks.audit_tasks import persist_audit_log
    persist_audit_log.delay({
        'tenant_id': str(current_user['tenant_id']),
        'event_type': 'user.invited',
        'resource_type': 'invitation',
        'actor_id': str(current_user['id']),
        'resource_id': str(invitation.id),
        'details': {'email': request.email, 'role': request.role, 'team_id': str(request.team_id) if request.team_id else None},
        'ip_address': req.client.host if req.client else None,
        'user_agent': req.headers.get('User-Agent')
    })
    
    return InviteUserResponse(
        invitation_id=invitation.id,
        email=invitation.email,
        status="sent",
        message=f"Invitation sent to {request.email}",
        team_id=invitation.team_id
    )


@router.get("/list", response_model=List[InvitationListResponse])
async def list_invitations(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all invitations for current tenant
    
    - Requires invitations:read permission
    - Shows pending and accepted invitations
    """
    # Check permission
    if not await has_permission(current_user['id'], 'invitations', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view invitations"
        )
    
    invitations = await invitation_service.list_tenant_invitations(
        db=db,
        tenant_id=current_user['tenant_id']
    )
    
    return [
        InvitationListResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            invited_by=inv.invited_by,
            team_id=inv.team_id,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            created_at=inv.created_at
        )
        for inv in invitations
    ]


@router.delete("/{invitation_id}")
async def cancel_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel/delete a pending invitation
    
    - Requires invitations:delete permission
    - Only pending invitations can be cancelled
    """
    # Check permission
    if not await has_permission(current_user['id'], 'invitations', 'delete', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel invitations"
        )
    
    await invitation_service.cancel_invitation(
        db=db,
        invitation_id=invitation_id,
        tenant_id=current_user['tenant_id']
    )
    
    return {"message": "Invitation cancelled successfully"}


@router.post("/resend/{invitation_id}")
async def resend_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend invitation email
    
    - Requires invitations:write permission
    - Only pending, non-expired invitations
    """
    # Check permission
    if not await has_permission(current_user['id'], 'invitations', 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to resend invitations"
        )
    
    # Get and validate invitation
    invitation = await invitation_service.get_invitation_for_resend(
        db=db,
        invitation_id=invitation_id,
        tenant_id=current_user['tenant_id']
    )
    
    # Get tenant for email
    tenant = await tenant_service.get_tenant_by_id(db, current_user['tenant_id'])
    
    # Resend invitation email via Celery (async)
    send_invitation_email.delay(
        invitation_id=str(invitation.id),
        tenant_id=str(current_user['tenant_id'])
    )
    
    return {"message": f"Invitation resent to {invitation.email}"}


@router.get("/accept/{token}")
async def validate_invitation(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate invitation token (public endpoint)
    
    Returns MINIMAL invitation details for display (PII minimization)
    """
    # Bypass RLS - token is the security key
    await rls_service.set_platform_admin_context(db)
    
    result = await invitation_service.validate_invitation_token(db=db, token=token)
    
    return result


@router.post("/join")
async def join_tenant(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    decoded_token: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept invitation and join tenant (after SSO login)
    
    - Requires authentication (Firebase token)
    - Enforces EMAIL VERIFICATION (security fix)
    - Creates user from invitation if doesn't exist
    - Marks invitation as accepted with audit trail
    
    This endpoint handles new users who just completed SSO login
    """
    from core.utils.firebase import firebase_auth_service
    
    # Bypass RLS to find invitation globally
    await rls_service.set_platform_admin_context(db)
    
    # Extract user info from Firebase token
    user_info = firebase_auth_service.get_user_info(decoded_token)
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    name = user_info.get("name")
    email_verified = user_info.get("email_verified", False)
    
    if not firebase_uid or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Accept invitation and create user (service handles RLS context switch)
    result = await invitation_service.accept_invitation_and_create_user(
        db=db,
        token=token,
        firebase_uid=firebase_uid,
        email=email,
        name=name,
        email_verified=email_verified,
        client_ip=request.client.host if request.client else None
    )
    
    # Switch to invitation's tenant context for audit log
    await rls_service.set_tenant_context(db, result['tenant_id'])
    
    # Log audit event (async via Celery)
    from core.tasks.audit_tasks import persist_audit_log
    persist_audit_log.delay({
        'tenant_id': str(result['tenant_id']),
        'event_type': 'user.accepted_invite',
        'resource_type': 'invitation',
        'actor_id': str(result['user_id']),
        'resource_id': None,
        'details': {'email': email, 'role': result['role']},
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('User-Agent')
    })
    
    return {
        "message": "Successfully joined tenant",
        "tenant_id": result['tenant_id'],
        "role": result['role'],
        "team_id": result['team_id']
    }


# ============================================================================
# BULK INVITATIONS
# ============================================================================

@router.post("/bulk")
async def bulk_invite_users(
    file: UploadFile,
    send_emails: bool = True,
    auto_create_teams: bool = True,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload CSV file and create bulk invitations.
    
    Permission required: users:invite
    
    File format:
    - Required columns: email, role
    - Optional columns: team_name, team_role, name
    - Max 100 rows, max 2MB file size
    
    Returns:
        Job ID, results summary, and download URLs
    """
    # Check permission
    if not await has_permission(current_user['id'], 'users', 'invite', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite users"
        )
    
    # Get tenant
    tenant = await tenant_service.get_tenant_by_id(db, current_user['tenant_id'])
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Parse CSV
    parser = BulkInviteCSVParser()
    parsed_csv = await parser.parse_file(file)
    
    if not parsed_csv.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_failed",
                "message": "CSV validation failed",
                "errors": [error.dict() for error in parsed_csv.errors]
            }
        )
    
    # Business rules validation
    business_errors = await parser.validate_business_rules(
        rows=parsed_csv.rows,
        current_user=current_user,
        db=db,
        tenant_domain=tenant.domain
    )
    
    if business_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_failed",
                "message": "Business validation failed",
                "errors": [error.dict() for error in business_errors]
            }
        )
    
    # Set RLS context
    await rls_service.set_tenant_context(db, str(current_user['tenant_id']))
    
    # Create invitations
    result = await invitation_service.bulk_create_invitations(
        db=db,
        tenant_id=current_user['tenant_id'],
        rows=parsed_csv.rows,
        created_by=current_user['id'],
        tenant_domain=tenant.domain,
        auto_create_teams=auto_create_teams
    )
    
    # Commit all changes
    await db.commit()
    
    # Queue email sending (background)
    if send_emails and result['invitation_ids']:
        send_bulk_invitation_emails.delay(
            invitation_ids=result['invitation_ids'],
            tenant_id=str(current_user['tenant_id'])
        )
    
    # Return results
    return {
        "job_id": str(result['job_id']),
        "total_processed": result['total_processed'],
        "successful": result['successful'],
        "failed": result['failed'],
        "results": result['results'],
        "teams_created": result['teams_created'],
        "download_url": f"/api/b2b/invitations/bulk/{result['job_id']}/download",
        "failures_url": f"/api/b2b/invitations/bulk/{result['job_id']}/download/failures"
    }


@router.get("/bulk/template")
async def download_template():
    """Download CSV template for bulk invitations"""
    template = """email,role,team_name,team_role,name
# Example rows (remove these before uploading):
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


@router.get("/bulk/jobs")
async def list_bulk_jobs(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List bulk invite jobs for current tenant"""
    offset = (page - 1) * page_size
    jobs = await invitation_service.list_bulk_jobs(
        db=db,
        tenant_id=current_user['tenant_id'],
        limit=page_size,
        offset=offset
    )
    
    # Format results
    job_list = []
    for job in jobs:
        creator_result = await db.execute(
            select(UserModel).where(UserModel.id == job.created_by)
        )
        creator = creator_result.scalar_one_or_none()
        
        job_list.append({
            "job_id": str(job.id),
            "total_rows": job.total_rows,
            "successful": job.successful_count,
            "failed": job.failed_count,
            "created_at": job.created_at.isoformat(),
            "created_by": creator.email if creator else "Unknown"
        })
    
    return {
        "jobs": job_list,
        "total": len(job_list),
        "page": page,
        "page_size": page_size
    }


@router.get("/bulk/{job_id}")
async def get_bulk_job_status(
    job_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get bulk invite job status and summary"""
    job = await invitation_service.get_bulk_job(db, job_id, current_user['tenant_id'])
    
    creator_result = await db.execute(
        select(UserModel).where(UserModel.id == job.created_by)
    )
    creator = creator_result.scalar_one_or_none()
    
    return {
        "job_id": str(job.id),
        "status": "completed",
        "total_rows": job.total_rows,
        "successful": job.successful_count,
        "failed": job.failed_count,
        "created_at": job.created_at.isoformat(),
        "created_by": {
            "id": str(creator.id),
            "email": creator.email,
            "name": creator.name
        } if creator else None,
        "download_url": f"/api/b2b/invitations/bulk/{job.id}/download"
    }


@router.get("/bulk/{job_id}/download")
async def download_bulk_results(
    job_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download full bulk invite results as CSV"""
    job = await invitation_service.get_bulk_job(db, job_id, current_user['tenant_id'])
    
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['row', 'email', 'name', 'role', 'team_name', 'status', 'invitation_id', 'error']
    )
    writer.writeheader()
    
    for row_data in job.results.get('rows', []):
        writer.writerow({
            'row': row_data.get('row', ''),
            'email': row_data.get('email', ''),
            'name': row_data.get('name', ''),
            'role': row_data.get('role', ''),
            'team_name': row_data.get('team_name', ''),
            'status': row_data.get('status', ''),
            'invitation_id': row_data.get('invitation_id', ''),
            'error': row_data.get('error', '')
        })
    
    output.seek(0)
    filename = f"bulk_invite_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/bulk/{job_id}/download/failures")
async def download_failures(
    job_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download only failed rows for correction and re-upload"""
    job = await invitation_service.get_bulk_job(db, job_id, current_user['tenant_id'])
    
    failures = [
        row for row in job.results.get('rows', [])
        if row.get('status') == 'error'
    ]
    
    if not failures:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No failures found in this job"
        )
    
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['row', 'email', 'name', 'role', 'team_name', 'error']
    )
    writer.writeheader()
    
    for row in failures:
        writer.writerow({
            'row': row.get('row', ''),
            'email': row.get('email', ''),
            'name': row.get('name', ''),
            'role': row.get('role', ''),
            'team_name': row.get('team_name', ''),
            'error': row.get('error', '')
        })
    
    output.seek(0)
    filename = f"bulk_invite_failures_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
