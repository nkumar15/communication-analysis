/**
 * B2C Workspace API Client
 * Handles workspace management, team collaboration, and invitations
 */
import firebaseAuthService from '../firebase/b2cAuthService';

const API_BASE_URL = 'http://localhost:8002'; // B2C service runs on port 8002

class B2CWorkspaceClient {
    /**
     * Get authorization header with Firebase ID token
     */
    async getAuthHeaders(forceRefresh = false) {
        const token = await firebaseAuthService.getIdToken(forceRefresh);
        if (!token) {
            throw new Error('Not authenticated');
        }
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    }

    // ============================================================================
    // Billing
    // ============================================================================

    /**
     * Get workspace subscription
     */
    async getSubscription(workspaceId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/billing/subscription?workspace_id=${workspaceId}`, {
            method: 'GET',
            headers,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch subscription');
        }
        return response.json();
    }

    /**
     * Create checkout session
     */
    async createCheckoutSession(data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/billing/checkout`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create checkout session');
        }
        return response.json();
    }

    /**
     * Create portal session
     */
    async createPortalSession(returnUrl) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/billing/portal`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ return_url: returnUrl }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create portal session');
        }
        return response.json();
    }

    /**
     * Get available public plans
     */
    async getPlans() {
        const response = await fetch(`${API_BASE_URL}/api/b2c/plans`, {
            method: 'GET',
        });
        if (!response.ok) {
            throw new Error('Failed to fetch plans');
        }
        return response.json();
    }

    // ============================================================================
    // Workspace Management
    // ============================================================================

    /**
     * List user's workspaces (personal + team workspaces)
     */
    async getWorkspaces() {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces`, {
            method: 'GET',
            headers,
        });
        if (!response.ok) {
            throw new Error('Failed to fetch workspaces');
        }
        return response.json();
    }

    /**
     * Create new team workspace (requires Premium+)
     */
    async createWorkspace(data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create workspace');
        }
        return response.json();
    }

    /**
     * Get workspace details with members
     */
    async getWorkspaceDetails(workspaceId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}`, {
            method: 'GET',
            headers,
        });
        if (!response.ok) {
            throw new Error('Failed to fetch workspace details');
        }
        return response.json();
    }

    /**
     * Update workspace settings
     */
    async updateWorkspace(workspaceId, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update workspace');
        }
        return response.json();
    }

    /**
     * Delete workspace (owner only, not personal workspace)
     */
    async deleteWorkspace(workspaceId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}`, {
            method: 'DELETE',
            headers,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete workspace');
        }
    }

    // ============================================================================
    // Member Management
    // ============================================================================

    /**
     * List workspace members
     */
    async getWorkspaceMembers(workspaceId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/members`, {
            method: 'GET',
            headers,
        });
        if (!response.ok) {
            throw new Error('Failed to fetch members');
        }
        return response.json();
    }

    /**
     * Update member role
     */
    async updateMemberRole(workspaceId, userId, role) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/members/${userId}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify({ role }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update member role');
        }
        return response.json();
    }

    /**
     * Remove member from workspace
     */
    async removeMember(workspaceId, userId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/members/${userId}`, {
            method: 'DELETE',
            headers,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to remove member');
        }
    }

    // ============================================================================
    // Workspace Invitations
    // ============================================================================

    /**
     * Invite user to workspace by email
     */
    async inviteToWorkspace(workspaceId, email, role = 'member') {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/invite`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ email, role }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send invitation');
        }
        return response.json();
    }

    /**
     * Get invitation details by token (public endpoint)
     */
    async getInvitation(token) {
        const response = await fetch(`${API_BASE_URL}/api/b2c/invitations/${token}`, {
            method: 'GET',
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch invitation');
        }
        return response.json();
    }

    /**
     * Accept workspace invitation
     */
    async acceptInvitation(token) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/invitations/${token}/accept`, {
            method: 'POST',
            headers,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to accept invitation');
        }
        return response.json();
    }

    /**
     * Cancel invitation
     */
    async cancelInvitation(invitationId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/invitations/${invitationId}`, {
            method: 'DELETE',
            headers,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to cancel invitation');
        }
    }

    // ============================================================================
    // Projects (Todos)
    // ============================================================================

    /**
     * Create todo
     */
    async createTodo(workspaceId, data) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/todos`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create todo');
        }
        return response.json();
    }

    /**
     * Get todos
     */
    async getTodos(workspaceId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/todos`, {
            method: 'GET',
            headers,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch todos');
        }
        return response.json();
    }

    /**
     * Toggle todo completion
     */
    async toggleTodo(workspaceId, todoId, isCompleted) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/todos/${todoId}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify({ is_completed: isCompleted }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update todo');
        }
        return response.json();
    }

    /**
     * Delete todo
     */
    async deleteTodo(workspaceId, todoId) {
        const headers = await this.getAuthHeaders();
        const response = await fetch(`${API_BASE_URL}/api/b2c/workspaces/${workspaceId}/todos/${todoId}`, {
            method: 'DELETE',
            headers,
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete todo');
        }
    }
}

export default new B2CWorkspaceClient();
