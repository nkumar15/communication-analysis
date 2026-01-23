"""
Integration tests for NSE RAG Document Status API

Tests cover:
- Checking status of uploaded documents
- Authorization requirements
- Handling of nonexistent job IDs
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestDocumentStatus:
    """Test suite for document ingestion status endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_status_after_upload(self, api_client: AsyncClient, finance_trader_test_setup, mock_pdf_file):
        """Test checking status immediately after upload"""
        # First, upload a document
        file_content, filename, content_type = mock_pdf_file
        
        upload_response = await api_client.post(
            "/api/domain/finance_trader/rag/upload",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"},
            files={"file": (filename, file_content, content_type)},
            data={}
        )
        
        assert upload_response.status_code == 200
        job_id = upload_response.json()["job_id"]
        
        # Check status
        status_response = await api_client.get(
            f"/api/domain/finance_trader/rag/status/{job_id}",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"}
        )
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        # Status should be "pending" since we're not running workers
        assert data["status"] in ["pending", "processing", "completed", "failed"]
    
    @pytest.mark.asyncio
    async def test_get_status_nonexistent_job(self, api_client: AsyncClient, finance_trader_test_setup):
        """Test that querying nonexistent job_id returns 404"""
        fake_job_id = str(uuid4())
        
        response = await api_client.get(
            f"/api/domain/finance_trader/rag/status/{fake_job_id}",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_status_unauthorized(self, api_client: AsyncClient):
        """Test that status check requires authentication"""
        fake_job_id = str(uuid4())
        
        response = await api_client.get(
            f"/api/domain/finance_trader/rag/status/{fake_job_id}"
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_status_invalid_job_id_format(self, api_client: AsyncClient, finance_trader_test_setup):
        """Test that invalid job_id format is rejected"""
        response = await api_client.get(
            "/api/domain/finance_trader/rag/status/not-a-valid-uuid",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"}
        )
        
        # Should return 404 (Not Found) because job_id is typed as str and handled by logic
        assert response.status_code == 404
