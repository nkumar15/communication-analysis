import firebaseAuthService from '../firebase/authService';

// B2B Domain API URL (Port 8003)
// In production, this might be routed via Nginx /api/b2b/domain
let envUrl = process.env.REACT_APP_B2B_DOMAIN_API_URL || '';

// Runtime Fix for Local Development:
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    // If env var is missing or points to internal docker name, fallback to localhost:8003
    if (!envUrl || envUrl.includes('b2b-domain-api')) {
        envUrl = 'http://localhost:8003';
        console.warn('⚠️ b2bDomainClient: Using localhost:8003 for local development');
    }
}

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

    // Enron / Bank Surveillance Endpoints
    async investigateEmail(data) {
        // Correct endpoint path matches backend router mount
        return this.post('/api/b2b/domain/bank_surveillance/investigate', data);
    }
}

export default new B2BDomainService();
