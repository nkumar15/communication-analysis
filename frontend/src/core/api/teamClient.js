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
 * Team API Service
 */
const teamApi = {
    /**
     * Get team statistics
     */
    getStats: async () => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/stats`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load team statistics');
        }

        return response.json();
    },

    /**
     * Get available team roles
     */
    getTeamRoles: async () => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/team-roles`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load team roles');
        }

        return response.json();
    },

    /**
     * List all teams
     */
    listTeams: async () => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load teams');
        }

        return response.json();
    },

    /**
     * Create a new team
     */
    createTeam: async (data) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create team');
        }

        return response.json();
    },

    /**
     * Get team details
     */
    getTeam: async (teamId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/${teamId}`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load team details');
        }

        return response.json();
    },

    /**
     * Update team
     */
    updateTeam: async (teamId, data) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/${teamId}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update team');
        }

        return response.json();
    },

    /**
     * Delete team
     */
    deleteTeam: async (teamId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/${teamId}`, {
            method: 'DELETE',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete team');
        }
    },

    /**
     * List team members
     */
    listMembers: async (teamId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/${teamId}/members`, {
            method: 'GET',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load team members');
        }

        return response.json();
    },

    /**
     * Add member to team
     */
    addMember: async (teamId, userId, role = 'team_member') => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/${teamId}/members`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                user_id: userId,
                team_role: role
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add member');
        }

        return response.json();
    },

    /**
     * Remove member from team
     */
    removeMember: async (teamId, userId) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/${teamId}/members/${userId}`, {
            method: 'DELETE',
            headers,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to remove member');
        }
    },

    /**
     * Update member role
     */
    updateMemberRole: async (teamId, userId, role) => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/${teamId}/members/${userId}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify({
                team_role: role
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update member role');
        }

        return response.json();
    },

    /**
     * Move user between teams
     */
    moveUser: async (userId, fromTeamId, toTeamId, role = 'team_member') => {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2b/teams/members/${userId}/move`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                from_team_id: fromTeamId,
                to_team_id: toTeamId,
                team_role: role
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to move user');
        }

        return response.json();
    }
};

export default teamApi;
