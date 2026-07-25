import firebaseAuthService from '../firebase/authService';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

/**
 * Get authorization headers
 */
const getAuthHeaders = async () => {
    const token = await firebaseAuthService.getIdToken();
    if (!token) {
        throw new Error('Not authenticated');
    }
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };
};

export const accountApi = {
    /**
     * Get current account settings
     * @returns {Promise<Object>} Account settings
     */
    getSettings: async () => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/account`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch account settings');
        }

        return response.json();
    },

    /**
     * Update account settings
     * @param {Object} updates - Fields to update (name, logo_url)
     * @returns {Promise<Object>} Updated settings
     */
    updateSettings: async (updates) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/account`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(updates),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update account settings');
        }

        return response.json();
    }
};
