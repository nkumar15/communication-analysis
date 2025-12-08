import firebaseAuthService from '../firebase/authService';
import { Platform } from 'react-native';

const API_BASE_URL = 'http://10.0.2.2:8000'; // Android Emulator Host Loopback

class NativeApiService {

    // Helper to get auth headers with native token
    async getAuthHeaders() {
        const token = await firebaseAuthService.getIdToken();
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    }

    async validateActivationToken(token) {
        // Using fetch which is global in RN
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/validate/${token}`);
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Invalid activation token');
        }
        return response.json();
    }

    async getActivationTenantInfo(tenantId) {
        const response = await fetch(`${API_BASE_URL}/api/b2b/activation/tenant-info/${tenantId}`);
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Failed to get tenant info');
        }
        return response.json();
    }

    async syncUser() {
        console.log("Mock Sync User for Native");
        return { status: "synced" };
    }

    async completeActivation(token) {
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
        return response.json();
    }
}

export default new NativeApiService();
