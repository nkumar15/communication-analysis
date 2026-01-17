"""
E2E Tests for Bulk Invitations
"""
import pytest
from httpx import AsyncClient
from io import BytesIO

pytestmark = pytest.mark.asyncio

class TestBulkInvitations:
    """Test bulk invitation uploads"""

    async def test_bulk_invite_success(
        self,
        api_client: AsyncClient,
        db_session,
        b2b_tenant,
        b2b_tenant_owner_token
    ):
        """Test successful bulk invite upload"""
        from modules.b2b.services.team_service import create_team
        from modules.b2b.models.team_role_definition import TeamRoleDefinition
        
        # Create team "Eng"
        await create_team(
            db=db_session,
            tenant_id=b2b_tenant.id,
            name="Eng",
            description="Engineering Team"
        )
        
        # Create Team Roles
        for role_name in ["team_contributor", "team_reader"]:
            db_session.add(TeamRoleDefinition(
                tenant_id=b2b_tenant.id,
                name=role_name,
                display_name=role_name.replace("_", " ").title(),
                description=f"Role {role_name}"
            ))
            
        await db_session.commit()
        
        # Create CSV content - ALL rows must have valid team info per current implementation
        domain = b2b_tenant.domain
        csv_content = f"email,role,team_name,team_role,name\ntest1@{domain},member,Eng,team_contributor,Test User 1\ntest2@{domain},viewer,Eng,team_reader,Test User 2".encode('utf-8')
        
        files = {
            "file": ("invites.csv", csv_content, "text/csv")
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
            files=files,
            data={"send_emails": "false"}  # Correctly pass boolean as string for multipart/form-data
        )
        
        assert response.status_code == 200, f"Bulk upload failed: {response.json()}"
        data = response.json()
        assert "job_id" in data
        assert data["total_processed"] == 2
        assert data["successful"] == 2
        assert data["failed"] == 0
        
    async def test_bulk_invite_invalid_format(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token
    ):
        """Test uploading invalid file format"""
        files = {
            "file": ("invites.txt", b"not,a,csv", "text/plain")
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
            files=files
        )
        
        # FastAPI might return 422 for validation or the endpoint handles it
        # Based on typical implementations, file uploads might be validated or fail parsing
        # The router expects UploadFile, but parsing happens in service.
        # Let's see what it returns. If it relies on pandas/csv parsing, it might fail inside.
        # Ideally should be 400.
        
        # Actually proper behavior often is 400 if parsing fails
        assert response.status_code in [400, 422]

    async def test_bulk_invite_missing_columns(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token
    ):
        """Test CSV missing required columns"""
        csv_content = b"name,phone\nalice,123456"
        
        files = {
            "file": ("missing_cols.csv", csv_content, "text/csv")
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"},
            files=files
        )
        
        assert response.status_code == 400
        assert "Missing required columns" in response.json().get("detail", "")
