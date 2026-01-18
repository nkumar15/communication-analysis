"""
Integration tests for NSE RAG Document List API

Tests cover:
- Listing all documents for a tenant
- Empty list for new tenants
- Authorization requirements
"""
import pytest
from httpx import AsyncClient


class TestDocumentList:
    """Test suite for document listing endpoint"""
    
    @pytest.mark.asyncio
    async def test_list_documents_empty(self, api_client: AsyncClient, finance_trader_test_setup):
        """Test listing documents for tenant with no uploads"""
        response = await api_client.get(
            "/api/domain/finance_trader/rag/documents",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_list_documents_after_upload(self, api_client: AsyncClient, finance_trader_test_setup, mock_pdf_file):
        """Test listing documents after uploading one"""
        # Upload a document first
        file_content, filename, content_type = mock_pdf_file
        
        upload_response = await api_client.post(
            "/api/domain/finance_trader/rag/upload",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"},
            files={"file": (filename, file_content, content_type)},
            data={"company_name": "Test Corp"}
        )
        
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # List documents
        list_response = await api_client.get(
            "/api/domain/finance_trader/rag/documents",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"}
        )
        
        assert list_response.status_code == 200
        documents = list_response.json()
        assert isinstance(documents, list)
        assert len(documents) >= 1
        
        # Find our uploaded document
        doc_ids = [doc["id"] for doc in documents]
        assert document_id in doc_ids
        
        # Verify document structure
        uploaded_doc = next(doc for doc in documents if doc["id"] == document_id)
        assert uploaded_doc["filename"] == filename
        assert uploaded_doc["company_name"] == "Test Corp"
        assert "status" in uploaded_doc
    
    @pytest.mark.asyncio
    async def test_list_documents_multiple_uploads(self, api_client: AsyncClient, finance_trader_test_setup, mock_pdf_file):
        """Test listing after multiple document uploads"""
        file_content, filename, content_type = mock_pdf_file
        
        # Upload 3 documents
        uploaded_ids = []
        for i in range(3):
            file_content.seek(0)  # Reset file pointer
            response = await api_client.post(
                "/api/domain/finance_trader/rag/upload",
                headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"},
                files={"file": (f"doc_{i}.pdf", file_content, content_type)},
                data={}
            )
            assert response.status_code == 200
            uploaded_ids.append(response.json()["document_id"])
        
        # List documents
        list_response = await api_client.get(
            "/api/domain/finance_trader/rag/documents",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"}
        )
        
        assert list_response.status_code == 200
        documents = list_response.json()
        assert len(documents) >= 3
        
        # All uploaded documents should be in the list
        doc_ids = [doc["id"] for doc in documents]
        for uploaded_id in uploaded_ids:
            assert uploaded_id in doc_ids
    
    @pytest.mark.asyncio
    async def test_list_documents_unauthorized(self, api_client: AsyncClient):
        """Test that listing requires authentication"""
        response = await api_client.get("/api/domain/finance_trader/rag/documents")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_documents_ordering(self, api_client: AsyncClient, finance_trader_test_setup, mock_pdf_file):
        """Test that documents are ordered by creation time (newest first)"""
        file_content, filename, content_type = mock_pdf_file
        
        # Upload 2 documents
        first_response = await api_client.post(
            "/api/domain/finance_trader/rag/upload",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"},
            files={"file": ("first.pdf", file_content, content_type)},
            data={}
        )
        first_id = first_response.json()["document_id"]
        
        file_content.seek(0)
        second_response = await api_client.post(
            "/api/domain/finance_trader/rag/upload",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"},
            files={"file": ("second.pdf", file_content, content_type)},
            data={}
        )
        second_id = second_response.json()["document_id"]
        
        # List documents
        list_response = await api_client.get(
            "/api/domain/finance_trader/rag/documents",
            headers={"Authorization": f"Bearer {finance_trader_test_setup['token']}"}
        )
        
        documents = list_response.json()
        
        # Find positions of our documents
        doc_ids = [doc["id"] for doc in documents]
        first_pos = doc_ids.index(first_id)
        second_pos = doc_ids.index(second_id)
        
        # Second (newer) should come before first (older) in the list
        assert second_pos < first_pos
