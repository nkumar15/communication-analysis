import firebaseAuthService from '../firebase/authService';

const API_BASE_URL = 'http://localhost:8000';

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

/**
 * Invitation API Service
 */
const invitationApi = {
    /**
     * Invite a user to join tenant
     * @param {string} email - User email
     * @param {string} role - User role (manager)
     * @returns {Promise} Invitation response
     */
    inviteUser: async (email, role = 'manager', teamId = null) => {
        const headers = await getAuthHeaders();
        const body = { email, role };
        if (teamId) {
            body.team_id = teamId;
        }
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/invite`, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send invitation');
        }

        return response.json();
    },

    /**
     * Get list of invitations for current tenant
     * @returns {Promise} List of invitations
     */
    listInvitations: async () => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/list`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load invitations');
        }

        return response.json();
    },

    /**
     * Cancel a pending invitation
     * @param {number} invitationId - Invitation ID
     * @returns {Promise} Success message
     */
    cancelInvitation: async (invitationId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/${invitationId}`, {
            method: 'DELETE',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to cancel invitation');
        }

        return response.json();
    },

    /**
     * Resend invitation email
     * @param {number} invitationId - Invitation ID
     * @returns {Promise} Success message
     */
    resendInvitation: async (invitationId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/resend/${invitationId}`, {
            method: 'POST',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to resend invitation');
        }

        return response.json();
    },

    /**
     * Validate invitation token (public)
     * @param {string} token - Invitation token
     * @returns {Promise} Invitation details
     */
    validateInvitation: async (token) => {
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/accept/${token}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Invalid invitation');
        }

        return response.json();
    },

    /**
     * Join tenant after SSO login
     * @param {string} token - Invitation token
     * @returns {Promise} Join response
     */
    joinTenant: async (token) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/join?token=${token}`, {
            method: 'POST',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to join tenant');
        }

        return response.json();
    },

    /**
     * Get user statistics
     */
    getUserStats: async () => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/users/stats`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load statistics');
        }

        return response.json();
    },

    /**
     * Get list of all users
     */
    getUsers: async () => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/users/list`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load users');
        }

        return response.json();
    }
};

export default invitationApi;
