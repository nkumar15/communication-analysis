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
     * @param {string} role - User role (tenant role)
     * @param {string} teamId - Optional team ID for auto-assignment
     * @param {string} teamRole - Optional team role
     * @returns {Promise} Invitation response
     */
    inviteUser: async (email, role = 'viewer', teamId = null, teamRole = null) => {
        const headers = await getAuthHeaders();
        const body = { email, role };
        if (teamId) {
            body.team_id = teamId;
            if (teamRole) {
                body.team_role = teamRole;
            }
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
    },

    // ============================================================================
    // BULK INVITATIONS
    // ============================================================================

    /**
     * Upload CSV for bulk user invitations
     * @param {File} file - CSV file
     * @returns {Promise} Bulk invite job result
     */
    bulkInviteUsers: async (file) => {
        const token = await firebaseAuthService.getIdToken();
        if (!token) {
            throw new Error('Not authenticated');
        }

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/bulk`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                // Note: Don't set Content-Type for FormData - browser sets it with boundary
            },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            // Handle validation errors with detailed row information
            if (error.detail?.error === 'validation_failed' && error.detail?.errors) {
                const validationError = new Error(error.detail.message || 'Validation failed');
                validationError.validationErrors = error.detail.errors;
                validationError.isValidationError = true;
                throw validationError;
            }
            throw new Error(error.detail?.message || error.detail || 'Failed to process bulk invitations');
        }

        return response.json();
    },

    /**
     * Download CSV template for bulk invitations
     * @returns {Promise<Blob>} CSV file blob
     */
    downloadTemplate: async () => {
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/bulk/template`, {
            method: 'GET',
        });

        if (!response.ok) {
            throw new Error('Failed to download template');
        }

        return response.blob();
    },

    /**
     * Get list of bulk invite jobs
     * @param {number} page - Page number
     * @param {number} pageSize - Items per page
     * @returns {Promise} List of bulk jobs
     */
    getBulkJobs: async (page = 1, pageSize = 20) => {
        const headers = await getAuthHeaders();
        const response = await fetch(
            `${API_BASE_URL}/api/b2b/invitations/bulk/jobs?page=${page}&page_size=${pageSize}`,
            { method: 'GET', headers }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load bulk jobs');
        }

        return response.json();
    },

    /**
     * Get bulk job status
     * @param {string} jobId - Job UUID
     * @returns {Promise} Job details
     */
    getBulkJobStatus: async (jobId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/bulk/${jobId}`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get job status');
        }

        return response.json();
    },

    /**
     * Download bulk job results as CSV
     * @param {string} jobId - Job UUID
     * @returns {Promise<Blob>} CSV file blob
     */
    downloadBulkResults: async (jobId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/bulk/${jobId}/download`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            throw new Error('Failed to download results');
        }

        return response.blob();
    },

    /**
     * Download only failed rows as CSV
     * @param {string} jobId - Job UUID
     * @returns {Promise<Blob>} CSV file blob
     */
    downloadBulkFailures: async (jobId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/invitations/bulk/${jobId}/download/failures`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('No failures to download');
            }
            throw new Error('Failed to download failures');
        }

        return response.blob();
    }
};

export default invitationApi;
