import firebaseAuthService from '../firebase/authService';

// B2B Domain API URL (Port 8003)
// In production, this might be routed via Nginx /api/b2b/domain
let envUrl = process.env.REACT_APP_B2B_DOMAIN_API_URL || '';

// Local Development: 
// Rely on webpack proxy or REACT_APP_B2B_DOMAIN_API_URL being set correctly.

const API_BASE_URL = envUrl;

class B2BDomainService {
    async getAuthHeaders() {
        const token = await firebaseAuthService.getIdToken();
        if (!token) throw new Error('Not authenticated');
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    }

    async post(path, data) {
        const headers = await this.getAuthHeaders();
        const url = `${API_BASE_URL}${path}`;
        console.log('🌐 [b2bDomainClient] POST:', url, data);
        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.text();
            let errorMsg = `Request failed: ${response.status}`;
            try {
                const json = JSON.parse(error);
                errorMsg = json.detail || errorMsg;
            } catch (e) { }
            throw new Error(errorMsg);
        }
        return response.json();
    }

    // Communication Domain Endpoints (Replaces Enron)
    async getCommunications(params) {
        // params: { limit, offset }
        const queryParams = new URLSearchParams(params).toString();
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/communications?${queryParams}`, { headers });
        if (!response.ok) throw new Error(`Failed to fetch communications: ${response.status}`);
        return response.json();
    }

    async getMessage(id) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/messages/${id}`, { headers });
        if (!response.ok) throw new Error(`Failed to fetch message: ${response.status}`);
        return response.json();
    }

    // Communication Analysis (AI Engine)
    async analyzeCommunication(data) {
        // Expected data: { text, metadata, tenant_id }
        return this.post('/api/b2b/domain/bank_surveillance/analyze', data);
    }

    // Legacy alias
    async investigateCommunication(data) {
        return this.analyzeCommunication(data);
    }

    // Legacy alias
    async investigateEmail(data) {
        return this.investigateCommunication(data);
    }

    // Search (RAG)
    async searchCommunications(params) {
        // params: { q, limit }
        const queryParams = new URLSearchParams(params).toString();
        const headers = await this.getAuthHeaders();
        const url = `${API_BASE_URL}/api/b2b/domain/bank_surveillance/search?${queryParams}`;

        const response = await fetch(url, {
            method: 'GET',
            headers
        });

        if (!response.ok) throw new Error(`Search failed: ${response.status}`);
        return response.json();
    }

    // Graph
    async buildGraph() {
        return this.post('/api/b2b/domain/bank_surveillance/graph/build', {});
    }

    async getGraphSummary() {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/graph/summary`, { headers });
        return response.json();
    }

    // Ingestion
    async getIngestionStats() {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/ingestion/stats`, { headers });
        if (!response.ok) throw new Error(`Failed to fetch stats: ${response.status}`);
        return response.json();
    }

    async getIngestionJobs(limit = 20) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/ingestion/jobs?limit=${limit}`, { headers });
        if (!response.ok) throw new Error(`Failed to fetch jobs: ${response.status}`);
        return response.json();
    }

    async triggerIngestion(data) {
        // data: { date, file_path?, force? }
        return this.post('/api/b2b/domain/bank_surveillance/ingestion/trigger', data);
    }

    async retryIngestion(jobId) {
        return this.post(`/api/b2b/domain/bank_surveillance/ingestion/retry/${jobId}`, {});
    }

    async _get(path, params = {}) {
        const headers = await this.getAuthHeaders();
        const query = new URLSearchParams(params).toString();
        const url = `${API_BASE_URL}/api/b2b/domain/bank_surveillance${path}${query ? '?' + query : ''}`;
        console.log('🌐 [b2bDomainClient] GET:', url);
        const response = await fetch(url, { headers });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        return response.json();
    }

    // Alerts
    async getAlerts(params = {}) {
        return this._get('/alerts/', params);
    }

    async getAlertStats() {
        return this._get('/alerts/stats');
    }

    async getAlert(id) {
        return this._get(`/alerts/${id}`);
    }

    async updateAlert(id, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/alerts/${id}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error(`Failed to update alert: ${response.status}`);
        return response.json();
    }

    async escalateAlert(id) {
        return this.post(`/api/b2b/domain/bank_surveillance/alerts/${id}/escalate`, {});
    }

    async closeAlert(id) {
        return this.post(`/api/b2b/domain/bank_surveillance/alerts/${id}/close`, {});
    }

    // Case Management
    async getCases(params = {}) {
        return this._get('/cases/', params);
    }

    async getCaseStats() {
        return this._get('/cases/stats');
    }

    async getCase(id) {
        return this._get(`/cases/${id}`);
    }

    async createCase(data) {
        return this.post('/api/b2b/domain/bank_surveillance/cases/', data);
    }

    async updateCase(id, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/cases/${id}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Failed to update case: ${response.status}`);
        }
        return response.json();
    }

    async addCaseNote(id, data) {
        return this.post(`/api/b2b/domain/bank_surveillance/cases/${id}/notes`, data);
    }

    async addCaseEvidence(id, data) {
        return this.post(`/api/b2b/domain/bank_surveillance/cases/${id}/evidence`, data);
    }

    // Regulatory Library
    async getRegulatoryDocuments(params = {}) {
        const queryParams = new URLSearchParams(params).toString();
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/regulatory/?${queryParams}`, { headers });
        if (!response.ok) throw new Error(`Failed to fetch regulatory documents: ${response.status}`);
        return response.json();
    }

    async createRegulatoryDocument(data) {
        return this.post('/api/b2b/domain/bank_surveillance/regulatory/', data);
    }

    // Surveillance Controls
    async getSurveillanceControls(params = {}) {
        const queryParams = new URLSearchParams(params).toString();
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/domain/bank_surveillance/controls/?${queryParams}`, { headers });
        if (!response.ok) throw new Error(`Failed to fetch surveillance controls: ${response.status}`);
        return response.json();
    }

    async createSurveillanceControl(data) {
        return this.post('/api/b2b/domain/bank_surveillance/controls/', data);
    }
}

export default new B2BDomainService();
