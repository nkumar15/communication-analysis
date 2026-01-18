/**
 * Finance Trader API Client (B2C)
 * Handles NSE/RAG functionality
 */
import firebaseAuthService from '../firebase/b2cAuthService';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

class FinanceTraderClient {
    /**
     * Get authorization header with Firebase ID token
     */
    async getAuthHeaders(forceRefresh = false) {
        const token = await firebaseAuthService.getIdToken(forceRefresh);
        if (!token) {
            throw new Error('Not authenticated');
        }
        return {
            'Authorization': `Bearer ${token}`,
            // 'Content-Type': 'application/json', // Let fetch set this for FormData, manual for JSON
        };
    }

    /**
     * List RAG documents
     */
    async listDocuments(domain = 'finance_trader') {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/domain/finance_trader/rag/documents`, {
            method: 'GET',
            headers: { ...headers, 'Content-Type': 'application/json' },
        });
        if (!response.ok) {
            throw new Error('Failed to fetch documents');
        }
        return response.json();
    }

    /**
     * Upload RAG document
     */
    async uploadDocument(domain = 'finance_trader', formData) {
        const headers = await this.getAuthHeaders();
        // Do NOT set Content-Type for FormData, browser sets it with boundary
        const response = await fetch(`${API_BASE_URL}/api/b2c/domain/finance_trader/rag/upload`, {
            method: 'POST',
            headers,
            body: formData,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload document');
        }
        return response.json();
    }

    /**
     * Get RAG Status
     */
    async getStatus(domain = 'finance_trader', jobId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/domain/finance_trader/rag/status/${jobId}`, {
            method: 'GET',
            headers: { ...headers, 'Content-Type': 'application/json' },
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get status');
        }
        return response.json();
    }

    /**
     * Search RAG
     */
    async search(domain = 'finance_trader', query) {
        const headers = await this.getAuthHeaders();
        const formData = new FormData();
        formData.append('query', query);

        const response = await fetch(`${API_BASE_URL}/api/b2c/domain/finance_trader/rag/search`, {
            method: 'POST',
            headers, // No Content-Type for FormData
            body: formData,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to search');
        }
        return response.json();
    }
}

export default new FinanceTraderClient();
