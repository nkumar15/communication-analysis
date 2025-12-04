import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import invitationApi from '../../../core/api/invitationClient';
import b2bClient from '../../../core/api/b2bClient';
import StatCard from '../../../core/components/StatCard';
import TabNav from '../../platform/components/TabNav';
import RoleBadge from '../../../core/components/RoleBadge';
import StatusBadge from '../../../core/components/StatusBadge';
import ActionMenu from '../components/ActionMenu';
import AdminLayout from '../layouts/AdminLayout';
import { useAuth } from '../../../core/hooks/useAuth';
import { formatDateTime } from '../../../utils/dateUtils';
import TeamSelector from '../components/TeamSelector';

const InvitationsPage = () => {
    const [stats, setStats] = useState(null);
    const [users, setUsers] = useState([]);
    const [invitations, setInvitations] = useState([]);
    const [activeTab, setActiveTab] = useState('users');
    const [searchTerm, setSearchTerm] = useState('');
    const [roleFilter, setRoleFilter] = useState('all');
    const [statusFilter, setStatusFilter] = useState('all');
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [email, setEmail] = useState('');
    const [availableRoles, setAvailableRoles] = useState([
        { value: 'admin', label: 'Admin', disabled: false },
        { value: 'viewer', label: 'Viewer', disabled: false }
    ]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [selectedRole, setSelectedRole] = useState('admin');
    const [selectedTeam, setSelectedTeam] = useState('');
    const [selectedTeamRole, setSelectedTeamRole] = useState('team_member');
    const navigate = useNavigate();
    const { user, getInvitableRoles, getScopeLabel } = useAuth();

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            setError('');

            // Load stats and users (all users can access)
            const [statsData, usersData] = await Promise.all([
                invitationApi.getUserStats(),
                invitationApi.getUsers()
            ]);

            setStats(statsData);
            setUsers(usersData);

            // Fetch roles separately to not block main data load
            try {
                console.log('🔄 Fetching roles from API...');
                const rolesData = await b2bClient.getRoles();
                console.log('✅ Roles fetched from API:', rolesData);

                if (Array.isArray(rolesData) && rolesData.length > 0) {
                    // Format roles for dropdown
                    const roles = rolesData.map(r => ({
                        value: r.name,
                        label: r.display_name || r.name.charAt(0).toUpperCase() + r.name.slice(1),
                        disabled: r.name === 'owner' // Disable owner role
                    }));

                    console.log('📋 Formatted roles for dropdown:', roles);

                    // Ensure we have at least Admin and Viewer if API returns empty (fallback)
                    if (roles.length === 0) {
                        console.warn('⚠️ No roles returned from API, using fallback');
                        roles.push(
                            { value: 'admin', label: 'Admin', disabled: false },
                            { value: 'viewer', label: 'Viewer', disabled: false }
                        );
                    }

                    setAvailableRoles(roles);
                    console.log('✅ availableRoles state updated with', roles.length, 'roles');

                    // Set default role to first available non-disabled role
                    if (roles.length > 0) {
                        const defaultRole = roles.find(r => !r.disabled) || roles[0];
                        setSelectedRole(defaultRole.value);
                        console.log('✅ Default role set to:', defaultRole.value);
                    }
                } else {
                    console.warn('⚠️ Roles data is not a valid array or is empty:', rolesData);
                }
            } catch (err) {
                console.error('❌ Failed to load roles:', err);
                // Keep default roles on error
            }

            // Try to load invitations (admin only)
            try {
                const invitationsData = await invitationApi.listInvitations();
                setInvitations(invitationsData);
            } catch (err) {
                // If 403, user doesn't have permission - that's ok
                if (err.message && !err.message.includes('permission')) {
                    console.error('Failed to load invitations:', err);
                }
                setInvitations([]);
            }
        } catch (err) {
            console.error('Failed to load data:', err);
            setError('Failed to load data');
        } finally {
            setLoading(false);
        }
    };


    const handleInvite = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        try {
            // Send the selected role directly (new role names)
            await invitationApi.inviteUser(
                email,
                selectedRole,
                selectedTeam || null,
                selectedTeam ? selectedTeamRole : null  // Only send team_role if team selected
            );
            setSuccess(`Invitation sent to ${email}`);
            setEmail('');
            setSelectedTeam('');
            setSelectedTeamRole('team_member');  // Reset team role
            setShowInviteModal(false);
            await loadData();
        } catch (err) {
            setError(err.message || 'Failed to send invitation');
        }
    };

    const handleResend = async (invitationId) => {
        try {
            await invitationApi.resendInvitation(invitationId);
            setSuccess('Invitation resent successfully');
        } catch (err) {
            setError(err.message || 'Failed to resend invitation');
        }
    };

    const handleCancel = async (invitationId) => {
        if (!window.confirm('Are you sure you want to cancel this invitation?')) {
            return;
        }

        try {
            await invitationApi.cancelInvitation(invitationId);
            setSuccess('Invitation cancelled');
            await loadData();
        } catch (err) {
            setError(err.message || 'Failed to cancel invitation');
        }
    };

    const getInitials = (name, email) => {
        if (name) {
            return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        }
        return email[0].toUpperCase();
    };

    const formatDate = (dateString) => {
        if (!dateString) return '-';
        try {
            return formatDateTime(dateString);
        } catch (e) {
            return dateString;
        }
    };

    const filterData = (data, type) => {
        let filtered = data;

        // Search filter
        if (searchTerm) {
            filtered = filtered.filter(item => {
                const searchLower = searchTerm.toLowerCase();
                if (type === 'users') {
                    return (
                        item.name?.toLowerCase().includes(searchLower) ||
                        item.email.toLowerCase().includes(searchLower)
                    );
                } else {
                    return item.email.toLowerCase().includes(searchLower);
                }
            });
        }

        // Role filter
        if (roleFilter !== 'all') {
            filtered = filtered.filter(item => item.role === roleFilter);
        }

        // Status filter
        if (statusFilter !== 'all') {
            if (type === 'users') {
                filtered = filtered.filter(item => {
                    return statusFilter === 'active' ? item.is_active : !item.is_active;
                });
            } else {
                filtered = filtered.filter(item => {
                    const isPending = !item.accepted_at;
                    return statusFilter === 'pending' ? isPending : !isPending;
                });
            }
        }

        return filtered;
    };

    const filteredUsers = filterData(users, 'users');

    // Only show pending invitations (accepted invitations are already in Users tab)
    const pendingInvitations = invitations.filter(inv => !inv.accepted_at);
    const filteredInvitations = filterData(pendingInvitations, 'invitations');

    if (loading) {
        return (
            <div style={{ padding: '40px', textAlign: 'center' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                <p>Loading...</p>
            </div>
        );
    }

    return (
        <AdminLayout title="User & Invitation Management" subtitle="Manage team members and invitations">
            <div style={{ padding: '32px', maxWidth: '1400px', margin: '0 auto' }}>
                {/* Scope Indicator */}
                {user && (
                    <div style={{
                        backgroundColor: '#EEF2FF',
                        border: '1px solid #C7D2FE',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        marginBottom: '24px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}>
                        <span style={{ fontSize: '16px' }}>👥</span>
                        <span style={{ fontSize: '14px', color: '#4338CA' }}>
                            <strong>Viewing:</strong> {getScopeLabel()}
                        </span>
                    </div>
                )}

                {/* Statistics Cards */}
                {stats && (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                        gap: '20px',
                        marginBottom: '32px'
                    }}>
                        <StatCard icon="👥" label="Total Users" value={stats.total_users} color="#4F46E5" />
                        <StatCard icon="✅" label="Active Users" value={stats.active_users} color="#10B981" />
                        <StatCard icon="📨" label="Pending Invitations" value={stats.pending_invitations} color="#F59E0B" />
                        <StatCard icon="👔" label="Managers" value={stats.managers_count} color="#8B5CF6" />
                    </div>
                )}

                {/* Main Content Card */}
                <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
                    {/* Tab Navigation with Action Button */}
                    <div style={{ padding: '24px 24px 0 24px ' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                            <TabNav
                                tabs={[
                                    { id: 'users', label: 'Users', count: users.length },
                                    { id: 'invitations', label: 'Pending Invitations', count: pendingInvitations.length }
                                ]}
                                activeTab={activeTab}
                                onTabChange={setActiveTab}
                            />
                            <button
                                onClick={() => setShowInviteModal(true)}
                                className="button button-primary"
                                style={{ marginBottom: '16px' }}
                            >
                                + Invite User
                            </button>
                        </div>
                    </div>

                    {/* Filters */}
                    <div style={{ padding: '0 24px 24px 24px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        <input
                            type="text"
                            placeholder="🔍 Search by name or email..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            style={{
                                flex: '1 1 300px',
                                padding: '10px 16px',
                                border: '1px solid #D1D5DB',
                                borderRadius: '6px',
                                fontSize: '14px'
                            }}
                        />
                        <select
                            value={roleFilter}
                            onChange={(e) => setRoleFilter(e.target.value)}
                            style={{
                                padding: '10px 16px',
                                border: '1px solid #D1D5DB',
                                borderRadius: '6px',
                                fontSize: '14px',
                                backgroundColor: 'white'
                            }}
                        >
                            <option value="all">All Roles</option>
                            <option value="admin">Admin</option>
                            <option value="field_manager">Field Manager</option>
                            <option value="field_agent">Field Agent</option>
                        </select>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            style={{
                                padding: '10px 16px',
                                border: '1px solid #D1D5DB',
                                borderRadius: '6px',
                                fontSize: '14px',
                                backgroundColor: 'white'
                            }}
                        >
                            <option value="all">All Status</option>
                            {activeTab === 'users' ? (
                                <>
                                    <option value="active">Active</option>
                                    <option value="inactive">Inactive</option>
                                </>
                            ) : (
                                <>
                                    <option value="pending">Pending</option>
                                    <option value="accepted">Accepted</option>
                                </>
                            )}
                        </select>
                    </div>

                    {/* Alerts */}
                    {error && (
                        <div style={{
                            margin: '0 24px 16px 24px',
                            padding: '12px 16px',
                            backgroundColor: '#FEE2E2',
                            border: '1px solid #FCA5A5',
                            borderRadius: '6px',
                            color: '#991B1B',
                            fontSize: '14px'
                        }}>
                            {error}
                        </div>
                    )}
                    {success && (
                        <div style={{
                            margin: '0 24px 16px 24px',
                            padding: '12px 16px',
                            backgroundColor: '#D1FAE5',
                            border: '1px solid #6EE7B7',
                            borderRadius: '6px',
                            color: '#065F46',
                            fontSize: '14px'
                        }}>
                            {success}
                        </div>
                    )}

                    {/* Users Table */}
                    {activeTab === 'users' && (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>User</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Email</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Role</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Status</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Last Login</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'right', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredUsers.map((user) => (
                                        <tr key={user.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                            <td style={{ padding: '16px 24px' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                    <div style={{
                                                        width: '40px',
                                                        height: '40px',
                                                        borderRadius: '50%',
                                                        backgroundColor: '#E0E7FF',
                                                        color: '#4F46E5',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        fontWeight: '600',
                                                        fontSize: '14px'
                                                    }}>
                                                        {getInitials(user.name, user.email)}
                                                    </div>
                                                    <span style={{ fontWeight: '500', color: '#111827' }}>
                                                        {user.name || 'No name'}
                                                    </span>
                                                </div>
                                            </td>
                                            <td style={{ padding: '16px 24px', color: '#6B7280' }}>{user.email}</td>
                                            <td style={{ padding: '16px 24px' }}>
                                                <RoleBadge role={user.role} />
                                            </td>
                                            <td style={{ padding: '16px 24px' }}>
                                                <StatusBadge status={user.is_active} type="user" />
                                            </td>
                                            <td style={{ padding: '16px 24px', color: '#6B7280', fontSize: '14px' }}>
                                                {formatDate(user.last_login)}
                                            </td>
                                            <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                                                <ActionMenu
                                                    actions={[
                                                        { label: 'View Details', icon: '👁️', onClick: () => console.log('View', user.id) },
                                                        { label: 'Edit Role', icon: '✏️', onClick: () => console.log('Edit', user.id) }
                                                    ]}
                                                />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {filteredUsers.length === 0 && (
                                <div style={{ padding: '60px 24px', textAlign: 'center', color: '#9CA3AF' }}>
                                    No users found
                                </div>
                            )}
                        </div>
                    )}

                    {/* Invitations Table */}
                    {activeTab === 'invitations' && (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Email</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Role</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Status</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Sent</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Expires</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'right', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredInvitations.map((inv) => {
                                        const isPending = !inv.accepted_at;
                                        const isExpired = new Date(inv.expires_at) < new Date();
                                        const status = inv.accepted_at ? 'accepted' : (isExpired ? 'expired' : 'pending');

                                        return (
                                            <tr key={inv.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                <td style={{ padding: '16px 24px', fontWeight: '500', color: '#111827' }}>
                                                    {inv.email}
                                                </td>
                                                <td style={{ padding: '16px 24px' }}>
                                                    <RoleBadge role={inv.role} />
                                                </td>
                                                <td style={{ padding: '16px 24px' }}>
                                                    <StatusBadge status={status} type="invitation" />
                                                </td>
                                                <td style={{ padding: '16px 24px', color: '#6B7280', fontSize: '14px' }}>
                                                    {formatDate(inv.created_at)}
                                                </td>
                                                <td style={{ padding: '16px 24px', color: '#6B7280', fontSize: '14px' }}>
                                                    {formatDate(inv.expires_at)}
                                                </td>
                                                <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                                                    {isPending && (
                                                        <ActionMenu
                                                            actions={[
                                                                { label: 'Resend', icon: '📧', onClick: () => handleResend(inv.id) },
                                                                { label: 'Cancel', icon: '✖️', onClick: () => handleCancel(inv.id), danger: true }
                                                            ]}
                                                        />
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                            {filteredInvitations.length === 0 && (
                                <div style={{ padding: '60px 24px', textAlign: 'center', color: '#9CA3AF' }}>
                                    No invitations found
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Invite Modal */}
                {showInviteModal && (
                    <div style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(0, 0, 0, 0.6)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 1000,
                        padding: '20px'
                    }} onClick={() => setShowInviteModal(false)}>
                        <div style={{
                            width: '100%',
                            maxWidth: '520px',
                            background: 'white',
                            borderRadius: '16px',
                            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                            overflow: 'hidden'
                        }} onClick={(e) => e.stopPropagation()}>
                            {/* Header with Gradient */}
                            <div style={{
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                padding: '24px',
                                color: 'white'
                            }}>
                                <h2 style={{
                                    margin: 0,
                                    fontSize: '24px',
                                    fontWeight: '700',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '10px'
                                }}>
                                    <span style={{ fontSize: '28px' }}>✉️</span>
                                    Invite User
                                </h2>
                                <p style={{
                                    margin: '8px 0 0 0',
                                    fontSize: '14px',
                                    opacity: 0.9
                                }}>
                                    Send an invitation to join your team
                                </p>
                            </div>

                            {/* Form Body */}
                            <form onSubmit={handleInvite} style={{ padding: '28px' }}>
                                {/* Email Field */}
                                <div style={{ marginBottom: '24px' }}>
                                    <label style={{
                                        display: 'block',
                                        marginBottom: '8px',
                                        fontWeight: '600',
                                        fontSize: '14px',
                                        color: '#374151'
                                    }}>
                                        Email Address <span style={{ color: '#ef4444' }}>*</span>
                                    </label>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="colleague@yourcompany.com"
                                        required
                                        style={{
                                            width: '100%',
                                            padding: '12px 16px',
                                            border: '2px solid #e5e7eb',
                                            borderRadius: '8px',
                                            fontSize: '14px',
                                            backgroundColor: '#f9fafb',
                                            color: '#111827',
                                            transition: 'all 0.2s',
                                            outline: 'none'
                                        }}
                                        onFocus={(e) => {
                                            e.target.style.borderColor = '#667eea';
                                            e.target.style.backgroundColor = 'white';
                                        }}
                                        onBlur={(e) => {
                                            e.target.style.borderColor = '#e5e7eb';
                                            e.target.style.backgroundColor = '#f9fafb';
                                        }}
                                    />
                                    <small style={{
                                        color: '#6B7280',
                                        fontSize: '12px',
                                        display: 'block',
                                        marginTop: '6px',
                                        fontStyle: 'italic'
                                    }}>
                                        Must match your company domain
                                    </small>
                                </div>

                                {/* Role Field */}
                                <div style={{ marginBottom: '24px' }}>
                                    <label style={{
                                        display: 'block',
                                        marginBottom: '8px',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        color: '#374151'
                                    }}>
                                        Role <span style={{ color: '#ef4444' }}>*</span>
                                    </label>
                                    <select
                                        value={selectedRole}
                                        onChange={(e) => setSelectedRole(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '12px 16px',
                                            borderRadius: '8px',
                                            border: '2px solid #e5e7eb',
                                            fontSize: '14px',
                                            backgroundColor: '#f9fafb',
                                            color: '#111827',
                                            cursor: 'pointer',
                                            outline: 'none',
                                            transition: 'all 0.2s'
                                        }}
                                        onFocus={(e) => {
                                            e.target.style.borderColor = '#667eea';
                                            e.target.style.backgroundColor = 'white';
                                        }}
                                        onBlur={(e) => {
                                            e.target.style.borderColor = '#e5e7eb';
                                            e.target.style.backgroundColor = '#f9fafb';
                                        }}
                                    >
                                        {availableRoles.map(role => (
                                            <option
                                                key={role.id || role.value}
                                                value={role.name || role.value}
                                                disabled={role.disabled}
                                            >
                                                {role.display_name || role.label || role.name} {role.disabled ? '(Cannot Invite)' : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Team Assignment */}
                                <div style={{ marginBottom: '24px' }}>
                                    <TeamSelector
                                        value={selectedTeam}
                                        onChange={(teamId) => {
                                            setSelectedTeam(teamId);
                                            // Reset team role when team changes
                                            if (!teamId) setSelectedTeamRole('team_member');
                                        }}
                                        label="Assign to Team (Optional)"
                                    />
                                    <small style={{
                                        color: '#6B7280',
                                        fontSize: '12px',
                                        display: 'block',
                                        marginTop: '6px',
                                        fontStyle: 'italic'
                                    }}>
                                        💡 User will be added to this team upon accepting invitation
                                    </small>
                                </div>

                                {/* Team Role (conditional) */}
                                {selectedTeam && (
                                    <div style={{ marginBottom: '24px' }}>
                                        <label style={{
                                            display: 'block',
                                            marginBottom: '8px',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            color: '#374151'
                                        }}>
                                            Team Role <span style={{ color: '#ef4444' }}>*</span>
                                        </label>
                                        <select
                                            value={selectedTeamRole}
                                            onChange={(e) => setSelectedTeamRole(e.target.value)}
                                            style={{
                                                width: '100%',
                                                padding: '12px 16px',
                                                borderRadius: '8px',
                                                border: '2px solid #e5e7eb',
                                                fontSize: '14px',
                                                backgroundColor: '#f9fafb',
                                                color: '#111827',
                                                cursor: 'pointer',
                                                outline: 'none',
                                                transition: 'all 0.2s'
                                            }}
                                            onFocus={(e) => {
                                                e.target.style.borderColor = '#667eea';
                                                e.target.style.backgroundColor = 'white';
                                            }}
                                            onBlur={(e) => {
                                                e.target.style.borderColor = '#e5e7eb';
                                                e.target.style.backgroundColor = '#f9fafb';
                                            }}
                                        >
                                            <option value="team_member">Team Member</option>
                                            <option value="team_manager">Team Manager</option>
                                            <option value="team_viewer">Team Viewer</option>
                                        </select>
                                        <small style={{
                                            color: '#6B7280',
                                            fontSize: '12px',
                                            display: 'block',
                                            marginTop: '6px',
                                            fontStyle: 'italic'
                                        }}>
                                            This determines their permissions within the team
                                        </small>
                                    </div>
                                )}

                                {/* Field Manager Note */}
                                {user?.role === 'field_manager' && (
                                    <div style={{
                                        marginBottom: '24px',
                                        padding: '12px',
                                        background: '#fef3c7',
                                        border: '1px solid #fbbf24',
                                        borderRadius: '8px'
                                    }}>
                                        <small style={{
                                            color: '#92400e',
                                            fontSize: '13px',
                                            display: 'block',
                                            fontWeight: '500'
                                        }}>
                                            ℹ️ As a Field Manager, you can only invite Field Agents
                                        </small>
                                    </div>
                                )}

                                {/* Action Buttons */}
                                <div style={{
                                    display: 'flex',
                                    gap: '12px',
                                    justifyContent: 'flex-end',
                                    paddingTop: '8px'
                                }}>
                                    <button
                                        type="button"
                                        onClick={() => setShowInviteModal(false)}
                                        style={{
                                            padding: '12px 24px',
                                            borderRadius: '8px',
                                            border: '2px solid #e5e7eb',
                                            background: 'white',
                                            color: '#374151',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s'
                                        }}
                                        onMouseEnter={(e) => e.target.style.background = '#f3f4f6'}
                                        onMouseLeave={(e) => e.target.style.background = 'white'}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        style={{
                                            padding: '12px 28px',
                                            borderRadius: '8px',
                                            border: 'none',
                                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                            color: 'white',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            cursor: 'pointer',
                                            boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
                                            transition: 'all 0.2s'
                                        }}
                                        onMouseEnter={(e) => e.target.style.transform = 'translateY(-2px)'}
                                        onMouseLeave={(e) => e.target.style.transform = 'translateY(0)'}
                                    >
                                        📨 Send Invitation
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>
        </AdminLayout>
    );
};

export default InvitationsPage;
