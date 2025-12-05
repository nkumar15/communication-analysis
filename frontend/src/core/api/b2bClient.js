import firebaseAuthService from '../firebase/authService';

const API_BASE_URL = 'http://localhost:8000';

class ApiService {
    /**
     * Resolve tenant from email
     */
    async resolveTenant(email) {
        const response = await fetch(`${API_BASE_URL}/api/b2b/auth/resolve-tenant`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to resolve tenant');
        }

        return response.json();
    }

    /**
     * Get authorization header with Firebase ID token
     * @param {boolean} forceRefresh - Force token refresh
     */
    async getAuthHeaders(forceRefresh = false) {
        console.log('📤 Getting auth headers, forceRefresh:', forceRefresh);
        const token = await firebaseAuthService.getIdToken(forceRefresh);

        if (!token) {
            console.error('❌ No token available for auth headers');
            throw new Error('Not authenticated');
        }

        console.log('✅ Auth headers ready with token');
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    }

    /**
     * Get current user info from backend
     */
    async getCurrentUser() {
        try {
            // Check if this is a platform admin - don't call B2B endpoint
            const tenantId = localStorage.getItem('firebase_tenant_id');
            const isPlatformAdmin = tenantId && (tenantId.includes('platform') || tenantId.includes('system'));

            if (isPlatformAdmin) {
                console.log('⚠️ b2bClient: Skipping getCurrentUser for platform admin');
                return null;
            }

            const headers = await this.getAuthHeaders();

            const response = await fetch(`${API_BASE_URL}/api/b2b/auth/me`, {
                method: 'GET',
                headers,
            });

            if (!response.ok) {
                if (response.status === 401) {
                    return null;
                }
                throw new Error('Failed to get user info');
            }

            return response.json();
        } catch (error) {
            console.error('Get user error:', error);
            return null;
        }
    }

    /**
     * Sync user data with backend
     * Call this after authentication to ensure user exists in database
     * @param {boolean} forceRefresh - Force token refresh (usually not needed)
     */
    async syncUser(forceRefresh = false) {
        try {
            console.log('🔄 Syncing user with backend...');
            const headers = await this.getAuthHeaders(forceRefresh);

            const response = await fetch(`${API_BASE_URL}/api/b2b/auth/sync-user`, {
                method: 'POST',
                headers,
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Sync user failed:', response.status, errorText);
                throw new Error(`Failed to sync user: ${response.status} - ${errorText}`);
            }

            const result = await response.json();
            console.log('✅ User synced successfully:', result);
            return result;
        } catch (error) {
            console.error('❌ Sync user error:', error);
            throw error;
        }
    }

    /**
     * Logout (just clear Firebase auth, backend is stateless now)
     */
    async logout() {
        await firebaseAuthService.signOut();
    }

    // Generic GET request with auth headers
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

    // Generic POST request with auth headers
    async post(path, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${path}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`POST ${path} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }

    // Convenience methods for roles and farmers
    async getRoles() {
        return this.get('/api/b2b/roles');
    }

    async getRoleTemplates() {
        return this.get('/api/b2b/roles/templates');
    }

    async createRole(data) {
        return this.post('/api/b2b/roles', data);
    }

    async deleteRole(roleId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/roles/${roleId}`, {
            method: 'DELETE',
            headers,
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`DELETE /api/b2b/roles/${roleId} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }

    async updateRolePermissions(roleId, permissions) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/roles/${roleId}/permissions`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ permissions }),
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`PUT /api/b2b/roles/${roleId}/permissions failed: ${response.status} - ${error}`);
        }
        return response.json();
    }

    async getResources() {
        return this.get('/api/b2b/roles/resources/all');
    }

    async getActions() {
        return this.get('/api/b2b/roles/actions/all');
    }

    async getFarmers() {
        return this.get('/api/b2b/farmers');
    }

    /**
     * Get audit logs with pagination and filtering
     * @param {Object} params - { page, limit, event_type, start_date, end_date }
     */
    async getAuditLogs(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                query.append(key, value);
            }
        });
        return this.get(`/api/b2b/audit-logs?${query.toString()}`);
    }

    /**
     * Export audit logs as CSV
     * @param {Object} params - { event_type, start_date, end_date }
     */
    async exportAuditLogs(params = {}) {
        const headers = await this.getAuthHeaders();
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                query.append(key, value);
            }
        });

        const response = await fetch(`${API_BASE_URL}/api/b2b/audit-logs/export?${query.toString()}`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Export failed: ${response.status} - ${error}`);
        }

        // Return blob for download
        return response.blob();
    }
}

export default new ApiService();
