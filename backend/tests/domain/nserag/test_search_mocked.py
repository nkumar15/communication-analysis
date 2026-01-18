"""
Integration tests for NSE RAG Search API (Mocked)

Tests search endpoint with mocked RAG service to avoid dependency on ingested documents.
This allows fast, deterministic testing of the search endpoint and synthesis logic.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestSearchEndpointMocked:
    """Test suite for search endpoint with mocked RAG service"""
    
    @pytest.mark.asyncio
    async def test_search_basic_query(self, api_client: AsyncClient, nse_test_setup, mocker):
        """Test search with basic query and mocked results"""
        # Mock rag_service.search() to return fake results
        mock_search_result = {
            "query": "What is the revenue?",
            "results": [
                {
                    "text": "Total revenue for Q3 FY25 was $150M, up 20% YoY.",
                    "score": 0.95,
                    "metadata": {
                        "company_name": "Test Corp",
                        "fiscal_year": "FY25",
                        "report_type": "quarterly"
                    }
                },
                {
                    "text": "Revenue growth was driven by strong product sales.",
                    "score": 0.87,
                    "metadata": {"company_name": "Test Corp"}
                }
            ],
            "count": 2
        }
        
        mocker.patch(
            'modules.domains.b2c.finance_trader.services.rag_service.rag_service.search',
            return_value=mock_search_result
        )
        
        # Call search endpoint
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": "What is the revenue?", "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "answer" in data  # Synthesized answer from SynthesisService
        assert "context" in data  # Retrieved context
        assert "query" in data
        assert data["query"] == "What is the revenue?"
        
        # Verify context contains mocked results
        assert len(data["context"]) == 2
        assert data["context"][0]["text"] == "Total revenue for Q3 FY25 was $150M, up 20% YoY."
    
    @pytest.mark.asyncio
    async def test_search_with_limit(self, api_client: AsyncClient, nse_test_setup, mocker):
        """Test search respects limit parameter"""
        mock_search_result = {
            "query": "test query",
            "results": [
                {"text": f"Result {i}", "score": 0.90 - (i * 0.1), "metadata": {}}
                for i in range(3)  # Return 3 results
            ],
            "count": 3
        }
        
        mock_search = mocker.patch(
            'modules.domains.b2c.finance_trader.services.rag_service.rag_service.search',
            return_value=mock_search_result
        )
        
        # Request with limit=3
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": "test query", "limit": 3}
        )
        
        assert response.status_code == 200
        
        # Verify search was called with correct limit
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args.kwargs.get('limit') == 3
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, api_client: AsyncClient, nse_test_setup, mocker):
        """Test search handles no results gracefully"""
        # Mock empty results
        mock_search_result = {
            "query": "no results query",
            "results": [],
            "count": 0
        }
        
        mocker.patch(
            'modules.domains.b2c.finance_trader.services.rag_service.rag_service.search',
            return_value=mock_search_result
        )
        
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": "no results query"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still have answer (even if it says "no information found")
        assert "answer" in data
        assert data["context"] == []
    
    @pytest.mark.asyncio
    async def test_search_unauthorized(self, api_client: AsyncClient, mocker):
        """Test search requires authentication"""
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            data={"query": "test query"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_search_missing_query(self, api_client: AsyncClient, nse_test_setup):
        """Test search rejects missing query parameter"""
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"limit": 5}  # Missing query
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_search_with_metadata_enrichment(self, api_client: AsyncClient, nse_test_setup, mocker):
        """Test search results include enriched metadata"""
        mock_search_result = {
            "query": "HDFC margins",
            "results": [
                {
                    "text": "HDFC Bank reported net interest margin of 4.2%",
                    "score": 0.92,
                    "metadata": {
                        "company_name": "HDFC Bank",
                        "fiscal_year": "FY24",
                        "period": "Q4",
                        "report_type": "earnings",
                        "page_number": 5
                    }
                }
            ],
            "count": 1
        }
        
        mocker.patch(
            'modules.domains.b2c.finance_trader.services.rag_service.rag_service.search',
            return_value=mock_search_result
        )
        
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": "HDFC margins"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify metadata is included in context
        assert len(data["context"]) == 1
        context = data["context"][0]
        assert context["metadata"]["company_name"] == "HDFC Bank"
        assert context["metadata"]["fiscal_year"] == "FY24"
        assert context["metadata"]["report_type"] == "earnings"


class TestSearchInputValidation:
    """Test input validation for search endpoint"""
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, api_client: AsyncClient, nse_test_setup):
        """Test that empty query string is rejected"""
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": ""}
        )
        
        # Should reject empty query
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_search_invalid_limit(self, api_client: AsyncClient, nse_test_setup):
        """Test that invalid limit values are rejected"""
        # Negative limit
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": "test", "limit": -1}
        )
        
        assert response.status_code == 422
        
        # Zero limit
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": "test", "limit": 0}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_search_very_long_query(self, api_client: AsyncClient, nse_test_setup, mocker):
        """Test search handles very long queries"""
        # Mock to avoid actual search
        mocker.patch(
            'modules.domains.b2c.finance_trader.services.rag_service.rag_service.search',
            return_value={"query": "long query", "results": [], "count": 0}
        )
        
        long_query = "What is " * 1000  # Very long query
        
        response = await api_client.post(
            "/api/domain/nse/rag/search",
            headers={"Authorization": f"Bearer {nse_test_setup['token']}"},
            data={"query": long_query}
        )
        
        # Should either accept or reject gracefully (not crash)
        assert response.status_code in [200, 422, 413]  # OK, Validation Error, or Payload Too Large
