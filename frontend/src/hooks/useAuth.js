import { useState, useEffect } from 'react';
import apiService from '../services/api';

/**
 * Custom hook for authentication and authorization
 * Provides current user info, role checking, and permission helpers
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
            dashboard: ['admin', 'field_manager'],
            users: ['admin', 'field_manager'],
            roles: ['admin', 'field_manager'],
            farmers: ['admin', 'field_manager', 'field_agent']
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
            case 'admin':
                return 'All Users (Organization-wide)';
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

        if (user.role === 'admin') {
            return [
                { value: 'admin', label: 'Admin' },
                { value: 'field_manager', label: 'Field Manager' },
                { value: 'field_agent', label: 'Field Agent' }
            ];
        }

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
