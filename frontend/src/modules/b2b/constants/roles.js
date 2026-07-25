/**
 * B2B Role Constants
 * 
 * Centralized role definitions for tenant-level and team-level roles.
 * Always use these constants instead of hardcoded strings.
 */

// Tenant-Level Roles (Organization-wide)
export const TENANT_ROLES = {
    OWNER: 'owner',
    ADMIN: 'admin',
    MEMBER: 'member',
    VIEWER: 'viewer'
};

// Tenant Role Display Names
export const TENANT_ROLE_LABELS = {
    [TENANT_ROLES.OWNER]: 'Owner',
    [TENANT_ROLES.ADMIN]: 'Admin',
    [TENANT_ROLES.MEMBER]: 'Member',
    [TENANT_ROLES.VIEWER]: 'Viewer'
};

// Team-Level Roles (Within a team)
export const TEAM_ROLES = {
    TEAM_MANAGER: 'team_manager',
    TEAM_CONTRIBUTOR: 'team_contributor',
    TEAM_READER: 'team_reader'
};

// Team Role Display Names
export const TEAM_ROLE_LABELS = {
    [TEAM_ROLES.TEAM_MANAGER]: 'Team Manager',
    [TEAM_ROLES.TEAM_CONTRIBUTOR]: 'Team Contributor',
    [TEAM_ROLES.TEAM_READER]: 'Team Reader'
};

/**
 * Get display name for tenant role
 * @param {string} role - Role slug (e.g., 'admin')
 * @returns {string} Display name (e.g., 'Admin')
 */
export const getTenantRoleLabel = (role) => {
    return TENANT_ROLE_LABELS[role] || role;
};

/**
 * Get display name for team role
 * @param {string} role - Role slug (e.g., 'team_manager')
 * @returns {string} Display name (e.g., 'Team Manager')
 */
export const getTeamRoleLabel = (role) => {
    return TEAM_ROLE_LABELS[role] || role;
};

/**
 * Check if role is tenant-level
 * @param {string} role
 * @returns {boolean}
 */
export const isTenantRole = (role) => {
    return Object.values(TENANT_ROLES).includes(role);
};

/**
 * Check if role is team-level
 * @param {string} role
 * @returns {boolean}
 */
export const isTeamRole = (role) => {
    return Object.values(TEAM_ROLES).includes(role);
};

/**
 * Check if user has sufficient tenant-level privilege
 * @param {string} userRole - User's current role
 * @param {string} requiredRole - Minimum required role
 * @returns {boolean}
 */
export const hasMinimumTenantRole = (userRole, requiredRole) => {
    const hierarchy = [
        TENANT_ROLES.VIEWER,
        TENANT_ROLES.MEMBER,
        TENANT_ROLES.ADMIN,
        TENANT_ROLES.OWNER
    ];

    const userLevel = hierarchy.indexOf(userRole);
    const requiredLevel = hierarchy.indexOf(requiredRole);

    return userLevel >= requiredLevel;
};
