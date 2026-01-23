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
from datetime import datetime, timezone

from core.db.session import get_db
from core.middleware import get_current_user
from modules.b2b.middleware import get_current_active_user
from modules.b2b.services.invitation_service import invitation_service
from modules.b2b.services.tenant_service import tenant_service
from modules.b2b.schemas.invitation import (
    InviteUserRequest,
    InviteUserResponse,
    InvitationListResponse
)
from modules.b2b.rbac import has_permission
from infrastructure.email import email_service
from core.config import settings
from core.db.rls import rls_service
from modules.b2b.utils.csv_parser import BulkInviteCSVParser
from workers.b2b_worker.email_tasks import send_bulk_invitation_emails, send_invitation_email
from modules.b2b.models import UserModel
from workers.b2b_worker.audit_tasks import persist_audit_log


router = APIRouter(prefix="/invitations", tags=["invitations"])


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
    
    # Capture response data before commit (RLS context is lost after commit)
    res_id = invitation.id
    res_email = invitation.email
    res_team_id = invitation.team_id
    
    # Commit transaction so background tasks can see the data
    await db.commit()
    
    # Send invitation email via Celery (async)
    send_invitation_email.delay(
        invitation_id=str(res_id),
        tenant_id=str(current_user['tenant_id'])
    )
    
    # Log audit event via Celery (async)
    # Log audit event via Celery (async)
    # from workers.b2b_worker.audit_tasks import persist_audit_log
    
    try:
        persist_audit_log.delay({
            'tenant_id': str(current_user['tenant_id']),
            'event_type': 'user.invited',
            'resource_type': 'invitation',
            'actor_id': str(current_user['id']),
            'resource_id': str(res_id),
            'details': {'email': request.email, 'role': request.role, 'team_id': str(request.team_id) if request.team_id else None},
            'ip_address': req.client.host if req.client else None,
            'user_agent': req.headers.get('User-Agent')
        })
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logging.getLogger(__name__).error(f"Failed to trigger audit log: {e}")
    
    return InviteUserResponse(
        invitation_id=res_id,
        email=res_email,
        status="sent",
        message=f"Invitation sent to {request.email}",
        team_id=res_team_id

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
    if not await has_permission(current_user['id'], 'users', 'read', db):
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
    if not await has_permission(current_user['id'], 'users', 'invite', db):
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
    if not await has_permission(current_user['id'], 'users', 'invite', db):
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
    
    # Capture email before commit
    res_email = invitation.email
    res_id = invitation.id

    # Commit transaction so background tasks can see the data
    await db.commit()
    
    # Resend invitation email via Celery (async)
    send_invitation_email.delay(
        invitation_id=str(res_id),
        tenant_id=str(current_user['tenant_id'])
    )
    
    return {"message": f"Invitation resent to {res_email}"}


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
    # Process join request via service
    result = await invitation_service.process_join_request(
        db=db,
        invitation_token=token,
        decoded_auth_token=decoded_token,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get('User-Agent')
    )
    
    # Capture response data
    res_tenant_id = result['tenant_id']
    res_role = result['role']
    res_team_id = result['team_id']
    res_user_id = result['user_id']
    
    # Commit transaction so background tasks can see the data
    await db.commit()
    
    # Audit log should be triggered here or in service. 
    # Since commit happens here, triggering here is safer for consistency with current pattern.
    from workers.b2b_worker.audit_tasks import persist_audit_log
    persist_audit_log.delay({
        'tenant_id': str(res_tenant_id),
        'event_type': 'user.accepted_invite',
        'resource_type': 'invitation',
        'actor_id': str(res_user_id),
        'resource_id': None,
        'details': {'email': result.get('email', 'unknown'), 'role': res_role}, # Email might not be in result, checking service return...
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('User-Agent')
    })
    
    return {
        "message": "Successfully joined tenant",
        "tenant_id": res_tenant_id,
        "role": res_role,
        "team_id": res_team_id
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
    # Process bulk invites via service
    result = await invitation_service.process_bulk_invites(
        db=db,
        tenant_id=current_user['tenant_id'],
        file=file,
        current_user=current_user,
        send_emails=send_emails
    )
    
    # Commit all changes
    await db.commit()
    
    # Queue email sending (background)
    if send_emails and result.get('invitation_ids'):
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
        "download_url": f"/invitations/bulk/{result['job_id']}/download",
        "failures_url": f"/invitations/bulk/{result['job_id']}/download/failures"
    }


@router.get("/bulk/template")
async def download_template():
    """Download CSV template for bulk invitations"""
    template = """email,team_name,team_role,role,name
# Example rows (remove these before uploading):
alice@yourdomain.com,Engineering,team_manager,,Alice Smith
bob@yourdomain.com,Engineering,team_contributor,admin,Bob Jones
carol@yourdomain.com,Sales,team_reader,,Carol White
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
        "download_url": f"/invitations/bulk/{job.id}/download"
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
    filename = f"bulk_invite_results_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    
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
        if row.get('status') == 'failed'
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
    filename = f"bulk_invite_failures_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
