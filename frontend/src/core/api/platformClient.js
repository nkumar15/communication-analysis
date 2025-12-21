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
     * Get B2B platform statistics (enterprise tenants)
     */
    async getB2BStats() {
        return this.get('/api/platform/b2b/stats');
    }

    /**
     * Get B2C platform statistics (personal workspaces)
     */
    async getB2CStats() {
        return this.get('/api/platform/b2c/stats');
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
        return this.get(`/api/platform/b2b/tenants?${params.toString()}`);
    }

    /**
     * Create a new tenant
     */
    async createTenant(tenantData) {
        return this.post('/api/platform/b2b/tenants', tenantData);
    }

    /**
     * Impersonate a tenant admin
     */
    async impersonateTenant(tenantId) {
        return this.post(`/api/platform/b2b/tenants/${tenantId}/impersonate`);
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
        return this.post('/api/platform/b2b/tenants/onboard', tenantData);
    }

    /**
     * Get tenant details
     */
    async getTenantDetails(tenantId) {
        return this.get(`/api/platform/b2b/tenants/${tenantId}/details`);
    }

    /**
     * Resend activation email
     */
    async resendActivation(tenantId) {
        return this.post(`/api/platform/b2b/tenants/${tenantId}/resend-activation`);
    }

    /**
     * Deactivate tenant
     */
    async deactivateTenant(tenantId) {
        return this.patch(`/api/platform/b2b/tenants/${tenantId}/deactivate`);
    }

    /**
     * Reactivate tenant
     */
    async reactivateTenant(tenantId) {
        return this.patch(`/api/platform/b2b/tenants/${tenantId}/reactivate`);
    }

    // ============================================================================
    // B2C Plan Management
    // ============================================================================

    /**
     * List all subscription plans (B2C)
     */
    async getPlans() {
        return this.get('/api/platform/b2c/plans');
    }

    /**
     * Create a new plan version
     */
    async createPlan(planData) {
        return this.post('/api/platform/b2c/plans', planData);
    }

    /**
     * Archive a plan version
     */
    async archivePlan(planId) {
        return this.post(`/api/platform/b2c/plans/${planId}/archive`);
    }

    // ============================================================================
    // B2B Plan Management
    // ============================================================================

    /**
     * List all subscription plans (B2B)
     */
    async getB2BPlans() {
        return this.get('/api/platform/b2b/plans');
    }

    /**
     * Create a new B2B plan version
     */
    async createB2BPlan(planData) {
        return this.post('/api/platform/b2b/plans', planData);
    }

    /**
     * Archive a B2B plan version
     */
    async archiveB2BPlan(planId) {
        return this.post(`/api/platform/b2b/plans/${planId}/archive`);
    }

    // ============================================================================
    // Unified Billing Management
    // ============================================================================

    /**
     * Search billing profiles (Tenants or Users)
     */
    async searchBillingProfiles(query, type) {
        const params = new URLSearchParams({ query });
        if (type) params.append('type', type);
        return this.get(`/api/platform/billing/profiles/search?${params.toString()}`);
    }

    /**
     * Get detailed billing profile
     */
    async getBillingProfile(id, type) {
        return this.get(`/api/platform/billing/profiles/${id}?type=${type}`);
    }

    /**
     * Send invoice email
     */
    async sendInvoice(id, type) {
        return this.post(`/api/platform/billing/invoices/${id}/send?type=${type}`);
    }

    /**
     * Refund invoice
     */
    async refundInvoice(id, type, reason) {
        return this.post(`/api/platform/billing/invoices/${id}/refund?type=${type}`, { reason });
    }

    /**
     * Cancel subscription
     */
    async cancelSubscription(id, type, reason, immediate = false) {
        return this.post(`/api/platform/billing/subscriptions/${id}/cancel?type=${type}`, {
            reason,
            immediate
        });
    }

    /**
     * Extend trial
     */
    async extendTrial(id, type, days) {
        return this.post(`/api/platform/billing/subscriptions/${id}/extend-trial?type=${type}`, {
            days
        });
    }

    /**
     * List coupons
     */
    async getCoupons(scope = 'all') {
        return this.get(`/api/platform/billing/coupons?scope=${scope}`);
    }

    /**
     * Create coupon
     */
    async createCoupon(data, scope) {
        return this.post(`/api/platform/billing/coupons?scope=${scope}`, data);
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
