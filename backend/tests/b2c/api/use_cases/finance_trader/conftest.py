"""
NSE RAG Domain Test Fixtures

Provides fixtures for testing NSE RAG endpoints:
- Mock PDF files for upload testing
- Test setup with tenant, user, and auth tokens
"""
import pytest
import pytest_asyncio
from io import BytesIO
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_test_tenant,
    create_test_user,
    TenantAwareSession,
    create_mock_firebase_token,
    encode_mock_jwt
)


@pytest_asyncio.fixture
async def finance_trader_test_setup(db_session: AsyncSession):
    """
    Setup NSE RAG test environment with tenant, admin user, and auth token.
    
    Returns:
        dict: Contains tenant, admin user, auth token, and tenant-aware session
    """
    # Create tenant
    tenant = await create_test_tenant(db_session)
    tenant_session = TenantAwareSession(db_session, tenant.id)
    
    # Create admin user
    admin = await create_test_user(
        tenant_session,
        tenant_id=tenant.id,
        email=f"nse-admin@{tenant.domain}",
        role_slug="admin"
    )
    
    # Create auth token
    token = encode_mock_jwt(create_mock_firebase_token(
        uid=admin.firebase_uid,
        email=admin.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    ))
    
    return {
        "tenant": tenant,
        "admin": admin,
        "token": token,
        "session": tenant_session,
        "tenant_id": tenant.id
    }


@pytest.fixture
def mock_pdf_file():
    """
    Create a minimal valid PDF file for testing.
    
    Returns:
        tuple: (file_content, filename, content_type)
    """
    # Minimal valid PDF structure (about 80 bytes)
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f\n"
        b"0000000009 00000 n\n"
        b"0000000058 00000 n\n"
        b"0000000115 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n187\n"
        b"%%EOF"
    )
    
    return BytesIO(pdf_content), "test_document.pdf", "application/pdf"


@pytest.fixture
def mock_pdf_with_metadata():
    """
    Create a mock PDF with metadata for testing metadata extraction.
    
    Returns:
        tuple: (file_content, filename, content_type, metadata)
    """
    file_obj, filename, content_type = mock_pdf_file()
    
    metadata = {
        "company_name": "Test Company Ltd",
        "report_type": "quarterly",
        "financial_period": "Q4 FY24"
    }
    
    return file_obj, filename, content_type, metadata
