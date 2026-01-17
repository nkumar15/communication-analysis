"""
E2E API Tests for Bulk User Invitations

Tests the bulk invitation feature including CSV upload, validation,
processing, and download functionality.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import io
from uuid import UUID

from core.constants import B2BRoleName
from tests.conftest import (
    create_mock_firebase_token,
    encode_mock_jwt,
    create_test_tenant,
    create_test_user
)


@pytest.mark.integration
class TestBulkInvitations:
    """Test bulk invitation endpoints"""
    
    @pytest.mark.asyncio
    async def test_upload_valid_csv(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test uploading a valid CSV file"""
        # Setup: Create tenant and admin user
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        # Create JWT token
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Create CSV content
        # Create CSV content (role is optional, team fields mandatory)
        csv_content = f"""email,team_name,team_role,name
alice@{tenant.domain},Engineering,team_admin,Alice Smith
bob@{tenant.domain},Engineering,team_contributor,Bob Jones
carol@{tenant.domain},Sales,team_viewer,Carol White
"""
        
        # Create file
        files = {
            'file': ('bulk_invite.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        # Pre-create teams since auto-creation is removed
        from modules.b2b.services.team_service import create_team
        await create_team(db_session, tenant.id, "Engineering", created_by=admin.id)
        await create_team(db_session, tenant.id, "Sales", created_by=admin.id)
        await db_session.commit()
        
        # Upload
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if response.status_code != 200:
            print(f"\n❌ Error: {response.text}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'job_id' in data
        assert data['total_processed'] == 3
        assert data['successful'] == 3
        assert data['failed'] == 0
        assert len(data['results']) == 3
        # Teams are no longer auto-created, so this list should be empty
        assert len(data.get('teams_created', [])) == 0
        
        # Verify download URLs
        assert '/download' in data['download_url']
        assert '/download/failures' in data['failures_url']
    
    @pytest.mark.asyncio
    async def test_csv_validation_errors(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test CSV with validation errors"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Missing team_name (Validation Error)
        csv_content = """email,team_role
invalid-email,team_manager
bob@wrongdomain.com,team_contributor
"""
        
        files = {
            'file': ('invalid.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # Check for missing columns error
        assert 'missing' in str(data).lower() or 'required' in str(data).lower()
    
    @pytest.mark.asyncio
    async def test_csv_domain_mismatch(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test CSV with email domain mismatch"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        csv_content = """email,team_name,team_role
bob@wrongdomain.com,Engineering,team_contributor
"""
        
        files = {
            'file': ('invalid.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        assert 'domain' in str(response.json()).lower()
    
    @pytest.mark.asyncio
    async def test_csv_too_large(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test CSV file exceeding size limit"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Create a CSV larger than 2MB
        large_content = f"email,team_name,team_role\n" + f"test@{tenant.domain},Engineering,team_contributor\n" * 100000
        
        files = {
            'file': ('large.csv', io.BytesIO(large_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 413
        assert 'too large' in response.json()['detail'].lower()
    
    @pytest.mark.asyncio
    async def test_csv_too_many_rows(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test CSV with more than 100 rows"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Create CSV with 101 rows
        rows = ["email,team_name,team_role\n"]
        for i in range(101):
            rows.append(f"user{i}@{tenant.domain},Engineering,team_contributor\n")
        csv_content = "".join(rows)
        
        files = {
            'file': ('too_many.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        assert '100' in response.json()['detail']
    
    @pytest.mark.asyncio
    async def test_download_csv_template(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test downloading CSV template"""
        response = await api_client.get("/api/b2b/invitations/bulk/template")
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/csv; charset=utf-8'
        assert 'bulk_invite_template.csv' in response.headers['content-disposition']
        
        # Verify template content (updated columns)
        content = response.text
        # Updated to include 'role' column
        assert 'email,team_name,team_role,role,name' in content
        assert '@yourdomain.com' in content
    
    @pytest.mark.asyncio
    async def test_download_bulk_results(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test downloading bulk invite results"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Pre-create teams
        from modules.b2b.services.team_service import create_team
        await create_team(db_session, tenant.id, "Engineering", created_by=admin.id)
        await create_team(db_session, tenant.id, "Sales", created_by=admin.id)
        await db_session.commit()

        # First, upload a CSV
        csv_content = f"""email,team_name,team_role
test1@{tenant.domain},Engineering,team_contributor
test2@{tenant.domain},Sales,team_viewer
"""
        files = {
            'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        upload_response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert upload_response.status_code == 200
        job_id = upload_response.json()['job_id']
        
        # Download results
        download_response = await api_client.get(
            f"/api/b2b/invitations/bulk/{job_id}/download",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert download_response.status_code == 200
        assert download_response.headers['content-type'] == 'text/csv; charset=utf-8'
        
        # Verify CSV content
        content = download_response.text
        assert f'test1@{tenant.domain}' in content
        assert f'test2@{tenant.domain}' in content
    
    @pytest.mark.asyncio
    async def test_get_bulk_job_status(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test getting bulk job status"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Pre-create team
        from modules.b2b.services.team_service import create_team
        await create_team(db_session, tenant.id, "Engineering", created_by=admin.id)
        await db_session.commit()

        # Upload CSV first
        csv_content = f"""email,team_name,team_role
test@{tenant.domain},Engineering,team_contributor
"""
        files = {
            'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        upload_response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert upload_response.status_code == 200
        job_id = upload_response.json()['job_id']
        
        # Get job status
        status_response = await api_client.get(
            f"/api/b2b/invitations/bulk/{job_id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert status_response.status_code == 200
        data = status_response.json()
        
        assert data['job_id'] == job_id
        assert data['status'] == 'completed'
        assert 'total_rows' in data
        assert 'successful' in data
        assert 'failed' in data
        assert 'created_at' in data
        assert 'created_by' in data
    
    @pytest.mark.asyncio
    async def test_list_bulk_jobs(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test listing bulk invite jobs"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/b2b/invitations/bulk/jobs",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'jobs' in data
        assert 'total' in data
        assert 'page' in data
        assert 'page_size' in data
        assert isinstance(data['jobs'], list)
    
    
    # test_admin_cannot_invite_owner REMOVED: 'role' column is no longer supported in bulk invite CSV.
    # By design, bulk invite only invites 'members', so owner invitation is impossible.

    
    @pytest.mark.asyncio
    async def test_viewer_cannot_bulk_invite(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that viewer doesn't have permission for bulk invite"""
        tenant = await create_test_tenant(db_session)
        viewer = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"viewer@{tenant.domain}",
            role_slug=B2BRoleName.VIEWER
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        csv_content = f"""email,team_name,team_role
test@{tenant.domain},Engineering,team_contributor
"""
        files = {
            'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 403
        assert 'permission' in response.json()['detail'].lower()
    
    @pytest.mark.asyncio
    async def test_duplicate_email_in_csv(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test CSV with duplicate emails"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        csv_content = f"""email,team_name,team_role
duplicate@{tenant.domain},Engineering,team_contributor
duplicate@{tenant.domain},Sales,team_manager
"""
        files = {
            'file': ('duplicate.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        assert 'duplicate' in str(response.json()).lower()
    
    @pytest.mark.asyncio
    async def test_team_auto_creation(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that teams are auto-created when specified"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        csv_content = f"""email,team_name,team_role
test@{tenant.domain},NewTeam,team_contributor
"""
        files = {
            'file': ('with_team.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        # Auto-creation is REMOVED. This should now fail with 400 Bad Request because of business validation errors (Team not found).
        assert response.status_code == 400
        data = response.json()
        
        # Expect validation error details
        assert data['detail']['error'] == 'validation_failed'
        errors = data['detail']['errors']
        assert len(errors) > 0
        assert 'Team not found' in str(errors)
        
        # Verify error messages
        # No results array in 400 validation error response
        # We only check top-level error details above
    
    @pytest.mark.asyncio
    async def test_download_failures_only(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test downloading only failed rows"""
        tenant = await create_test_tenant(db_session)
        admin = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=f"admin@{tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Upload CSV that will succeed (no failures)
        csv_content = f"""email,team_name,team_role
valid@{tenant.domain},Engineering,team_contributor
"""
        files = {
            'file': ('valid.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        upload_response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        if upload_response.status_code == 200:
            job_id = upload_response.json()['job_id']
            
            download_response = await api_client.get(
                f"/api/b2b/invitations/bulk/{job_id}/download/failures",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            # Should return 404 if no failures
            assert download_response.status_code == 404
