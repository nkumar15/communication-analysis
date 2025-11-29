import firebaseAuthService from '../firebase/authService';

const API_BASE_URL = 'http://localhost:8000';

class ApiService {
    /**
     * Resolve tenant from email
     */
    async resolveTenant(email) {
        const response = await fetch(`${API_BASE_URL}/api/auth/resolve-tenant`, {
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
            const headers = await this.getAuthHeaders();

            const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
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

            const response = await fetch(`${API_BASE_URL}/api/auth/sync-user`, {
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
        return this.get('/api/roles');
    }

    async getFarmers() {
        return this.get('/api/farmers');
    }
}

export default new ApiService();
