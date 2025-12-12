import firebaseAuthService from '../firebase/authService';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

/**
 * Platform Admin API Client
 * For platform-level operations (tenant management, platform stats, etc.)
 */
class PlatformApiService {
    /**
     * Get authorization header with Firebase ID token
     */
    async getAuthHeaders() {
        const token = await firebaseAuthService.getIdToken();
        if (!token) {
            throw new Error('Not authenticated');
        }
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    }

    /**
     * Get current platform admin user info
     */
    async getCurrentUser() {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${API_BASE_URL}/api/platform/auth/me`, {
                method: 'GET',
                headers,
            });

            if (!response.ok) {
                if (response.status === 401 || response.status === 404) {
                    return null;
                }
                throw new Error('Failed to get platform admin info');
            }

            return response.json();
        } catch (error) {
            console.error('Get platform admin error:', error);
            return null;
        }
    }

    /**
     * Get platform statistics
     */
    async getStats() {
        return this.get('/api/platform/stats');
    }

    /**
     * Get all tenants
     */
    async getTenants(skip = 0, limit = 20, search = '') {
        const params = new URLSearchParams({
            skip: skip.toString(),
            limit: limit.toString()
        });
        if (search) {
            params.append('search', search);
        }
        return this.get(`/api/platform/tenants?${params.toString()}`);
    }

    /**
     * Create a new tenant
     */
    async createTenant(tenantData) {
        return this.post('/api/platform/tenants', tenantData);
    }

    /**
     * Impersonate a tenant admin
     */
    async impersonateTenant(tenantId) {
        return this.post(`/api/platform/tenants/${tenantId}/impersonate`);
    }

    /**
     * Logout
     */
    async logout() {
        await firebaseAuthService.signOut();
    }

    /**
     * Generic GET request with auth headers
     */
    async get(path) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${path}`, {
            method: 'GET',
            headers,
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`GET ${path} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }

    /**
     * Generic POST request with auth headers
     */
    async post(path, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${path}`, {
            method: 'POST',
            headers,
            body: data ? JSON.stringify(data) : undefined
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`POST ${path} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }

    /**
     * Generic DELETE request with auth headers
     */
    async delete(path) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${path}`, {
            method: 'DELETE',
            headers,
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`DELETE ${path} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }
    /**
     * Onboard a new tenant (full workflow)
     */
    async onboardTenant(tenantData) {
        return this.post('/api/platform/tenants/onboard', tenantData);
    }

    /**
     * Get tenant details
     */
    async getTenantDetails(tenantId) {
        return this.get(`/api/platform/tenants/${tenantId}/details`);
    }

    /**
     * Resend activation email
     */
    async resendActivation(tenantId) {
        return this.post(`/api/platform/tenants/${tenantId}/resend-activation`);
    }

    /**
     * Deactivate tenant
     */
    async deactivateTenant(tenantId) {
        return this.patch(`/api/platform/tenants/${tenantId}/deactivate`);
    }

    /**
     * Generic PATCH request with auth headers
     */
    async patch(path, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${path}`, {
            method: 'PATCH',
            headers,
            body: data ? JSON.stringify(data) : undefined
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`PATCH ${path} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }
}

export default new PlatformApiService();
