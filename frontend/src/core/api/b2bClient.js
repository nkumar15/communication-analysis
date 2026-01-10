import firebaseAuthService from '../firebase/authService';

// Use environment variable for production, empty string for dev/test (uses webpack proxy)
// Set REACT_APP_API_URL in production to point to your backend
let envUrl = process.env.REACT_APP_API_URL || '';

// Runtime Fix for Local Development:
// If we are running on localhost (browser) but the API URL is set to an internal Docker hostname (b2b-api),
// it means the environment variable is polluted. We should ignore it and use the proxy.
if (typeof window !== 'undefined' &&
    window.location.hostname === 'localhost' &&
    envUrl &&
    (envUrl.includes('b2b-api') || envUrl.includes('b2c-api') || envUrl.includes('platform-api'))) {
    console.warn('⚠️ b2bClient: Ignoring Docker internal URL on localhost. Using proxy instead.', envUrl);
    envUrl = '';
}

const API_BASE_URL = envUrl;

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
     * Update user role
     */
    async updateUserRole(userId, role) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/users/${userId}/role`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ role }),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to update role: ${response.status} - ${error}`);
        }

        return response.json();
    }

    /**
     * Update user status (activate/deactivate)
     */
    async updateUserStatus(userId, isActive) {
        const headers = await this.getAuthHeaders();
        const action = isActive ? 'reactivate' : 'deactivate';

        // Use the new dedicated endpoints
        const response = await fetch(`${API_BASE_URL}/api/b2b/users/${userId}/${action}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({}), // Empty body
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to ${action} user: ${response.status} - ${error}`);
        }

        return response.json();
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

    // Generic PUT request with auth headers
    async put(path, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${path}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`PUT ${path} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }

    // Generic PATCH request with auth headers
    async patch(path, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}${path}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`PATCH ${path} failed: ${response.status} - ${error}`);
        }
        return response.json();
    }

    // Generic DELETE request with auth headers
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
        // DELETE returns 204 No Content, so check for empty response
        if (response.status === 204) {
            return null;
        }
        return response.json();
    }

    // Convenience methods for roles and projects
    async getRoles() {
        return this.get('/api/b2b/roles');
    }

    async getRoleTemplates() {
        return this.get('/api/b2b/roles/templates');
    }

    async getInvitableRoles() {
        return this.get('/api/b2b/roles/invitable');
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

    async getProjects() {
        return this.get('/api/b2b/projects');
    }

    /**
     * Get role-aware dashboard statistics
     */
    async getDashboardStats() {
        return this.get('/api/b2b/dashboard/stats');
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

    /**
     * Validate activation token
     * @param {string} token 
     */
    async validateActivationToken(token) {
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/validate/${token}`);
        if (!response.ok) {
            const text = await response.text();
            let errorMsg = 'Invalid activation token';
            try {
                const data = JSON.parse(text);
                errorMsg = data.detail || errorMsg;
            } catch (e) {
                if (text) errorMsg = text;
            }
            throw new Error(errorMsg);
        }
        return response.json();
    }

    /**
     * Get tenant info for activation (public)
     * @param {string} tenantId 
     */
    async getActivationTenantInfo(tenantId) {
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/tenant-info/${tenantId}`);
        if (!response.ok) {
            const text = await response.text();
            let errorMsg = 'Failed to get tenant info';
            try {
                const data = JSON.parse(text);
                errorMsg = data.detail || errorMsg;
            } catch (e) {
                if (text) errorMsg = text;
            }
            throw new Error(errorMsg);
        }
        return response.json();
    }

    /**
     * Complete activation process
     * @param {string} token 
     */
    async completeActivation(token) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/complete`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ activation_token: token }),
        });

        if (!response.ok) {
            const text = await response.text();
            let errorMsg = 'Activation failed';
            try {
                const data = JSON.parse(text);
                errorMsg = data.detail || errorMsg;
            } catch (e) {
                if (text) errorMsg = text;
            }
            throw new Error(errorMsg);
        }
        return response.json();
    }

    /**
     * Setup SSO during activation
     */
    async setupActivationSSO(payload) {
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/setup-sso`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const text = await response.text();
            let errorMsg = 'SSO configuration failed';
            try {
                const data = JSON.parse(text);
                errorMsg = data.detail || errorMsg;
            } catch (e) {
                if (text) errorMsg = text;
            }
            throw new Error(errorMsg);
        }
        return response.json();
    }

    /**
     * Create portal session
     */
    async createPortalSession(returnUrl) {
        return this.post('/api/b2b/billing/portal', { return_url: returnUrl });
    }

    /**
     * Helper to handle response and parse JSON
     */
    async handleResponse(response) {
        if (!response.ok) {
            const error = await response.text();
            try {
                const jsonError = JSON.parse(error);
                throw new Error(jsonError.detail || `API Request Failed: ${response.status}`);
            } catch (e) {
                if (e.message.includes('API Request Failed')) throw e;
                throw new Error(`API Request Failed: ${response.status} - ${error}`);
            }
        }
        return response.json();
    }

    /**
     * RAG: Upload Document
     */
    async uploadRagDocument(domain, formData) {
        // Use raw fetch for multipart/form-data to let browser set boundary
        const headers = await this.getAuthHeaders();
        delete headers['Content-Type']; // Let browser set it

        const response = await fetch(`${API_BASE_URL}/api/domain/${domain}/rag/upload`, {
            method: 'POST',
            headers,
            body: formData
        });

        if (!response.ok) {
            const error = await response.text();
            try {
                const jsonError = JSON.parse(error);
                throw new Error(jsonError.detail || `Upload failed: ${response.status}`);
            } catch (e) {
                throw new Error(`Upload failed: ${response.status} - ${error}`);
            }
        }
        return response.json();
    }

    /**
     * RAG: Get Job Status
     */
    async getRagStatus(domain, jobId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/domain/${domain}/rag/status/${jobId}`, {
            method: 'GET',
            headers
        });
        return this.handleResponse(response);
    }

    /**
     * RAG: Search
     */
    async searchRag(domain, query) {
        const headers = await this.getAuthHeaders();
        // Backend expects Form data for search
        delete headers['Content-Type']; // Let fetch set correct content type for FormData/URLSearchParams if needed, or set explicitly for x-www-form-urlencoded

        const formData = new URLSearchParams();
        formData.append('query', query);

        const response = await fetch(`${API_BASE_URL}/api/domain/${domain}/rag/search`, {
            method: 'POST',
            headers: {
                ...headers,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });
        return this.handleResponse(response);
    }

    /**
     * RAG: List Documents
     */
    async listRagDocuments(domain) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/domain/${domain}/rag/documents`, {
            method: 'GET',
            headers
        });
        return this.handleResponse(response);
    }
}

export default new ApiService();

