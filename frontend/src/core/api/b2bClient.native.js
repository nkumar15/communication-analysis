import firebaseAuthService from '../firebase/authService';

const API_BASE_URL = 'http://10.0.2.2:8000'; // Android Emulator Host Loopback

class NativeApiService {

    // Helper to get auth headers with native token
    async getAuthHeaders() {
        const token = await firebaseAuthService.getIdToken();
        if (!token) {
            throw new Error('Not authenticated - no Firebase token');
        }
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    }

    /**
     * Validate activation token (public endpoint)
     */
    async validateActivationToken(token) {
        console.log('📤 Validating token:', token);
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/validate/${token}`);
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Invalid activation token');
        }
        const result = await response.json();
        console.log('✅ Token validated:', result.tenant_name);
        return result;
    }

    /**
     * Get tenant info for activation (public endpoint)
     */
    async getActivationTenantInfo(tenantId) {
        console.log('📤 Getting tenant info:', tenantId);
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/tenant-info/${tenantId}`);
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Failed to get tenant info');
        }
        const result = await response.json();
        console.log('✅ Got tenant info:', result);
        return result;
    }

    /**
     * Sync user after authentication (protected endpoint)
     */
    async syncUser() {
        console.log('📤 Syncing user with backend');
        const headers = await this.getAuthHeaders();

        const response = await fetch(`${API_BASE_URL}/api/b2b/auth/sync-user`, {
            method: 'POST',
            headers,
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Sync user failed: ${error}`);
        }

        const result = await response.json();
        console.log('✅ User synced:', result);
        return result;
    }

    /**
     * Complete activation (protected endpoint)
     */
    async completeActivation(token) {
        console.log('📤 Completing activation');
        const headers = await this.getAuthHeaders();

        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/complete`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ activation_token: token }),
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Activation failed');
        }

        const result = await response.json();
        console.log('✅ Activation complete:', result);
        return result;
    }
}

export default new NativeApiService();
