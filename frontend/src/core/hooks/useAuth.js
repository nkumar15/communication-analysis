import { useState, useEffect } from 'react';
import apiService from '../api/b2bClient';
import { auth } from '../firebase/config';

/**
 * Custom hook for authentication and authorization
 * Provides current user info, role checking, and permission helpers
 * 
 * NOTE: This is for B2B users only. Platform admins should not use this hook.
 * 
 * The hook now uses permissions from the API response for component visibility,
 * rather than hardcoded role-to-permission mappings.
 */
export const useAuth = () => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadUser();
    }, []);

    const loadUser = async () => {
        try {
            setLoading(true);
            setError(null);

            // Check if this is a platform admin - skip B2B API call
            const tenantId = localStorage.getItem('firebase_tenant_id') || auth.tenantId;
            const isPlatformAdmin = tenantId && (tenantId.includes('platform') || tenantId.includes('system'));

            if (isPlatformAdmin) {
                console.log('⚠️ useAuth: Skipping B2B API call for platform admin');
                setUser(null);
                setLoading(false);
                return;
            }

            // API now returns permissions and teams
            const userData = await apiService.getCurrentUser();
            setUser(userData);
        } catch (err) {
            console.error('Failed to load user:', err);
            setError(err.message);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    /**
     * Check if user has one of the specified roles
     * @param {string|string[]} roles - Single role or array of roles
     * @returns {boolean}
     */
    const hasRole = (roles) => {
        if (!user || !user.role) return false;
        const rolesArray = Array.isArray(roles) ? roles : [roles];
        return rolesArray.includes(user.role);
    };

    /**
     * Check if user has a specific permission (resource:action format)
     * Uses the permissions array from /auth/me API response
     * 
     * @param {string} resource - Resource name (e.g., 'projects', 'users')
     * @param {string} action - Action name (e.g., 'read', 'write', 'delete')
     * @returns {boolean}
     * 
     * @example
     * hasPermission('projects', 'write')  // true if user can write projects
     * hasPermission('users', 'invite')    // true if user can invite users
     */
    const hasPermission = (resource, action) => {
        if (!user || !user.permissions) return false;
        return user.permissions.includes(`${resource}:${action}`);
    };

    /**
     * Check if user can access a specific feature
     * Maps feature names to required permissions
     * 
     * @param {string} feature - Feature name
     * @returns {boolean}
     */
    const canAccess = (feature) => {
        if (!user) return false;

        // Map features to required permissions
        const featurePermissions = {
            dashboard: 'dashboard:read',
            projects: 'projects:read',
            users: 'users:read',
            teams: 'teams:read',
            roles: 'roles:read',
            account: 'account:read',
            billing: 'billing:read',
            invoices: 'invoices:read',
            audit_logs: 'audit_logs:read',
            invitations: 'invitations:read',
            integrations: 'integrations:read',
            webhooks: 'webhooks:read',
            api_keys: 'api_keys:read',
            security: 'security:read',
            reports: 'reports:read',
            analytics: 'analytics:read',
            rag_documents: 'rag_documents:read',
            rag_nse: 'rag_nse:read',
            rag_enron: 'rag_enron:read'
        };

        const requiredPermission = featurePermissions[feature];
        if (!requiredPermission) {
            // Unknown feature - deny access by default for security
            return false;
        }

        const [resource, action] = requiredPermission.split(':');
        return hasPermission(resource, action);
    };

    /**
     * Get the user's teams
     * @returns {Array<{id: string, name: string, team_role: string}>}
     */
    const getTeams = () => {
        return user?.teams || [];
    };

    /**
     * Check if user is a manager in any team
     * @returns {boolean}
     */
    const isTeamManager = () => {
        return getTeams().some(t => t.team_role === 'team_manager');
    };

    /**
     * Get scope description for current user
     * Uses role_display_name from API for generic display
     * @returns {string}
     */
    const getScopeLabel = () => {
        if (!user) return 'Loading...';

        // Use role_display_name from backend (works for any use case)
        const roleDisplayName = user.role_display_name || user.role || 'Unknown Role';

        // Add context based on role type
        switch (user.role) {
            case 'owner':
                return `All Users (${roleDisplayName})`;
            case 'admin':
                return `Organization-wide (${roleDisplayName})`;
            default:
                return roleDisplayName;
        }
    };

    /**
     * Get available role options for invitations based on current user
     * @returns {Array<{value: string, label: string}>}
     */
    const getInvitableRoles = () => {
        if (!user) return [];

        // Check if user can invite
        if (!hasPermission('users', 'invite')) {
            return [];
        }

        if (user.role === 'owner') {
            return [
                { value: 'owner', label: 'Owner' },
                { value: 'admin', label: 'Admin' },
                { value: 'member', label: 'Member' },
                { value: 'viewer', label: 'Viewer' }
            ];
        }

        if (user.role === 'admin') {
            return [
                { value: 'admin', label: 'Admin' },
                { value: 'member', label: 'Member' },
                { value: 'viewer', label: 'Viewer' }
            ];
        }

        return [];
    };

    return {
        user,
        loading,
        error,
        hasRole,
        hasPermission,  // NEW: Check specific resource:action
        canAccess,
        getTeams,       // NEW: Get user's teams
        isTeamManager,  // NEW: Check if user manages any team
        getScopeLabel,
        getInvitableRoles,
        refresh: loadUser
    };
};

export default useAuth;
