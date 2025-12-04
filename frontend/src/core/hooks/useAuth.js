import { useState, useEffect } from 'react';
import apiService from '../api/b2bClient';
import { auth } from '../firebase/config';

/**
 * Custom hook for authentication and authorization
 * Provides current user info, role checking, and permission helpers
 * NOTE: This is for B2B users only. Platform admins should not use this hook.
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
     * Check if user can access a specific feature
     * @param {string} feature - Feature name (dashboard, users, roles, farmers)
     * @returns {boolean}
     */
    const canAccess = (feature) => {
        if (!user || !user.role) return false;

        const permissions = {
            dashboard: ['owner', 'admin', 'viewer', 'field_manager'], // All roles can view dashboard
            users: ['owner', 'admin', 'field_manager'], // Owner, Admin, and Field Manager can manage users
            roles: ['owner', 'admin', 'field_manager'], // Owner, Admin, and Field Manager can manage roles
            farmers: ['owner', 'admin', 'field_manager', 'field_agent'], // All except Viewer
            teams: ['owner', 'admin', 'viewer', 'field_manager', 'field_agent', 'manager', 'member'], // All roles can access teams
            account: ['owner', 'admin', 'viewer', 'field_manager', 'field_agent', 'manager', 'member'] // All roles can access account settings
        };

        return permissions[feature]?.includes(user.role) || false;
    };

    /**
     * Get scope description for current user
     * @returns {string}
     */
    const getScopeLabel = () => {
        if (!user) return 'Loading...';

        switch (user.role) {
            case 'owner':
                return 'All Users (Organization Owner)';
            case 'admin':
                return 'All Users (Organization-wide)';
            case 'viewer':
                return 'View Only';
            case 'field_manager':
                return 'Your Team';
            case 'field_agent':
                return 'My Data';
            default:
                return 'Unknown';
        }
    };

    /**
     * Get available role options for invitations based on current user
     * @returns {Array<{value: string, label: string}>}
     */
    const getInvitableRoles = () => {
        if (!user) return [];

        if (user.role === 'owner') {
            return [
                { value: 'owner', label: 'Owner' },
                { value: 'admin', label: 'Admin' },
                { value: 'viewer', label: 'Viewer' }
            ];
        }

        if (user.role === 'admin') {
            return [
                { value: 'admin', label: 'Admin' },
                { value: 'viewer', label: 'Viewer' }
            ];
        }

        // Legacy support for field_manager
        if (user.role === 'field_manager') {
            return [
                { value: 'field_agent', label: 'Field Agent' }
            ];
        }

        return [];
    };

    return {
        user,
        loading,
        error,
        hasRole,
        canAccess,
        getScopeLabel,
        getInvitableRoles,
        refresh: loadUser
    };
};

export default useAuth;
