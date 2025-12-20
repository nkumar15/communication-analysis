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
        csv_content = f"""email,role,team_name,team_role,name
alice@{tenant.domain},admin,Engineering,team_manager,Alice Smith
bob@{tenant.domain},member,Engineering,team_contributor,Bob Jones
carol@{tenant.domain},viewer,Sales,team_reader,Carol White
"""
        
        # Create file
        files = {
            'file': ('bulk_invite.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        # Upload
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'job_id' in data
        assert data['total_processed'] == 3
        assert data['successful'] == 3
        assert data['failed'] == 0
        assert len(data['results']) == 3
        assert 'Engineering' in data['teams_created']
        assert 'Sales' in data['teams_created']
        
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
        
        csv_content = """email,role,team_name
invalid-email,admin,Engineering
bob@wrongdomain.com,member,Sales
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
        
        assert 'validation_failed' in str(data).lower() or 'error' in str(data).lower()
    
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
        
        csv_content = """email,role
bob@wrongdomain.com,member
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
        large_content = f"email,role\n" + f"test@{tenant.domain},member\n" * 100000
        
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
        rows = ["email,role\n"]
        for i in range(101):
            rows.append(f"user{i}@{tenant.domain},member\n")
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
        
        # Verify template content
        content = response.text
        assert 'email,role,team_name,team_role,name' in content
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
        
        # First, upload a CSV
        csv_content = f"""email,role
test1@{tenant.domain},member
test2@{tenant.domain},viewer
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
        
        # Upload CSV first
        csv_content = f"""email,role
test@{tenant.domain},member
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
    
    @pytest.mark.asyncio
    async def test_admin_cannot_invite_owner(self, api_client: AsyncClient, db_session: AsyncSession):
        """Test that admin cannot invite users with owner role"""
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
        
        csv_content = f"""email,role
newowner@{tenant.domain},owner
"""
        files = {
            'file': ('owner.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        assert 'owner' in str(response.json()).lower() or 'admin' in str(response.json()).lower()
    
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
        
        csv_content = f"""email,role
test@{tenant.domain},member
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
        
        csv_content = f"""email,role
duplicate@{tenant.domain},member
duplicate@{tenant.domain},admin
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
        
        csv_content = f"""email,role,team_name,team_role
test@{tenant.domain},member,NewTeam,team_contributor
"""
        files = {
            'file': ('with_team.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')
        }
        
        response = await api_client.post(
            "/api/b2b/invitations/bulk",
            files=files,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify team was created
        assert 'NewTeam' in data.get('teams_created', [])
    
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
        csv_content = f"""email,role
valid@{tenant.domain},member
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
