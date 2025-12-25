import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import invitationApi from '../../../../core/api/invitationClient';
import b2bClient from '../../../../core/api/b2bClient';
import StatCard from '../../../../core/components/StatCard';
import TabNav from '../../../../shared/TabNav';
import RoleBadge from '../../../../core/components/RoleBadge';
import StatusBadge from '../../../../core/components/StatusBadge';
import ActionMenu from '../components/ActionMenu';
import AdminLayout from '../layouts/AdminLayout';
import { useAuth } from '../../../../core/hooks/useAuth';
import { TENANT_ROLES } from '../../constants/roles';
import { formatDateTime } from '../../../../utils/dateUtils';
import TeamSelector from '../components/TeamSelector';
import BulkInviteModal from '../components/BulkInviteModal';
import { InvitationsPageSkeleton } from '../../../../core/components/LoadingSkeleton';

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
        { value: TENANT_ROLES.ADMIN, label: 'Admin', disabled: false },
        { value: TENANT_ROLES.VIEWER, label: 'Viewer', disabled: false }
    ]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [selectedRole, setSelectedRole] = useState(TENANT_ROLES.MEMBER);
    const [selectedTeam, setSelectedTeam] = useState('');
    const [selectedTeamRole, setSelectedTeamRole] = useState('team_contributor');

    // Edit User Modal State
    const [showEditUserModal, setShowEditUserModal] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [newRole, setNewRole] = useState('');

    // Bulk Invite State
    const [showBulkInviteModal, setShowBulkInviteModal] = useState(false);
    const [bulkJobs, setBulkJobs] = useState([]);

    const navigate = useNavigate();
    const { user, getInvitableRoles, getScopeLabel, hasPermission } = useAuth();

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
                        disabled: r.name === TENANT_ROLES.OWNER // Disable owner role
                    }));

                    console.log('📋 Formatted roles for dropdown:', roles);

                    // Ensure we have at least Admin and Viewer if API returns empty (fallback)
                    if (roles.length === 0) {
                        console.warn('⚠️ No roles returned from API, using fallback');
                        roles.push(
                            { value: TENANT_ROLES.ADMIN, label: 'Admin', disabled: false },
                            { value: TENANT_ROLES.VIEWER, label: 'Viewer', disabled: false }
                        );
                    }

                    setAvailableRoles(roles);
                    console.log('✅ availableRoles state updated with', roles.length, 'roles');

                    // Set default role to 'member' if available, otherwise first non-disabled
                    if (roles.length > 0) {
                        const memberRole = roles.find(r => r.value === TENANT_ROLES.MEMBER && !r.disabled);
                        const defaultRole = memberRole || roles.find(r => !r.disabled) || roles[0];
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

            // Try to load bulk jobs (admin only)
            try {
                const bulkJobsData = await invitationApi.getBulkJobs();
                setBulkJobs(bulkJobsData.jobs || []);
            } catch (err) {
                console.error('Failed to load bulk jobs:', err);
                setBulkJobs([]);
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
            setSelectedTeamRole('team_contributor');  // Reset team role
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

    const handleEditUser = (user) => {
        setEditingUser(user);
        setNewRole(user.role);
        setShowEditUserModal(true);
    };

    const handleUpdateUserRole = async (e) => {
        e.preventDefault();
        if (!editingUser) return;

        setLoading(true);
        setError('');

        try {
            await b2bClient.updateUserRole(editingUser.id, newRole);
            setSuccess(`Role updated for ${editingUser.name || editingUser.email}`);
            setShowEditUserModal(false);
            setEditingUser(null);
            loadData();
        } catch (err) {
            setError(err.message || 'Failed to update user role');
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateUserStatus = async (user, newStatus) => {
        const action = newStatus ? 'activate' : 'deactivate';
        if (!window.confirm(`Are you sure you want to ${action} ${user.email}?`)) {
            return;
        }

        setLoading(true);
        setError('');

        try {
            await b2bClient.updateUserStatus(user.id, newStatus);
            setSuccess(`User ${action}d successfully`);
            await loadData();
        } catch (err) {
            setError(err.message || `Failed to ${action} user`);
        } finally {
            setLoading(false);
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
            <AdminLayout title="User & Invitation Management" subtitle="Manage team members and invitations">
                <InvitationsPageSkeleton />
            </AdminLayout>
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
                    {/* Tab Navigation with Action Buttons */}
                    <div style={{ padding: '24px 24px 0 24px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                            <TabNav
                                tabs={[
                                    { id: 'users', label: 'Users', count: users.length },
                                    { id: 'invitations', label: 'Pending Invitations', count: pendingInvitations.length },
                                    { id: 'bulk_history', label: 'Bulk History', count: bulkJobs.length }
                                ]}
                                activeTab={activeTab}
                                onTabChange={setActiveTab}
                            />
                            {/* Only show invite buttons if user has invite permission */}
                            {hasPermission('users', 'invite') && (
                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <button
                                        onClick={() => setShowInviteModal(true)}
                                        style={{
                                            backgroundColor: '#4F46E5',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '8px',
                                            padding: '10px 20px',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            cursor: 'pointer',
                                            boxShadow: '0 2px 4px rgba(79, 70, 229, 0.2)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            transition: 'all 0.2s'
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = '#4338CA';
                                            e.currentTarget.style.boxShadow = '0 4px 6px rgba(79, 70, 229, 0.3)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = '#4F46E5';
                                            e.currentTarget.style.boxShadow = '0 2px 4px rgba(79, 70, 229, 0.2)';
                                        }}
                                    >
                                        <span style={{ fontSize: '16px', fontWeight: 'bold' }}>+</span>
                                        Invite User
                                    </button>
                                    <button
                                        onClick={() => setShowBulkInviteModal(true)}
                                        style={{
                                            backgroundColor: '#10B981',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '8px',
                                            padding: '10px 20px',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            cursor: 'pointer',
                                            boxShadow: '0 2px 4px rgba(16, 185, 129, 0.2)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            transition: 'all 0.2s'
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = '#059669';
                                            e.currentTarget.style.boxShadow = '0 4px 6px rgba(16, 185, 129, 0.3)';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = '#10B981';
                                            e.currentTarget.style.boxShadow = '0 2px 4px rgba(16, 185, 129, 0.2)';
                                        }}
                                    >
                                        <span style={{ fontSize: '16px' }}>📋</span>
                                        Bulk Invite
                                    </button>
                                </div>
                            )}
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
                            <option value="member">Member</option>
                            <option value="viewer">Viewer</option>
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

                    {/* Error Message */}
                    {error && (
                        <div className="alert alert-error" style={{
                            maxWidth: '800px',
                            margin: '0 auto 24px auto',
                            padding: '16px',
                            borderRadius: '8px',
                            backgroundColor: '#FEE2E2',
                            color: '#B91C1C',
                            border: '1px solid #FECACA',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px'
                        }}>
                            <span>⚠️</span>
                            {error}
                            <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}>×</button>
                        </div>
                    )}

                    {/* Success Message */}
                    {success && (
                        <div className="alert alert-success" style={{
                            maxWidth: '800px',
                            margin: '0 auto 24px auto',
                            padding: '16px',
                            borderRadius: '8px',
                            backgroundColor: '#DCFCE7',
                            color: '#15803D',
                            border: '1px solid #BBF7D0',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px'
                        }}>
                            <span>✅</span>
                            {success}
                            <button onClick={() => setSuccess(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}>×</button>
                        </div>
                    )}    {/* Users Table */}
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
                                                        { label: 'Edit Role', icon: '✏️', onClick: () => handleEditUser(user) },
                                                        user.is_active
                                                            ? { label: 'Deactivate User', icon: '🚫', onClick: () => handleUpdateUserStatus(user, false), danger: true }
                                                            : { label: 'Activate User', icon: '✅', onClick: () => handleUpdateUserStatus(user, true) }
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

                    {/* Bulk History Table */}
                    {activeTab === 'bulk_history' && (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderTop: '1px solid #E5E7EB', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Date</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Total</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Successful</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Failed</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Created By</th>
                                        <th style={{ padding: '12px 24px', textAlign: 'right', fontSize: '12px', fontWeight: '600', color: '#6B7280', textTransform: 'uppercase' }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {bulkJobs.map((job) => (
                                        <tr key={job.job_id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                            <td style={{ padding: '16px 24px', fontWeight: '500', color: '#111827' }}>
                                                {formatDate(job.created_at)}
                                            </td>
                                            <td style={{ padding: '16px 24px', color: '#374151' }}>
                                                {job.total_rows}
                                            </td>
                                            <td style={{ padding: '16px 24px' }}>
                                                <span style={{
                                                    padding: '4px 10px',
                                                    backgroundColor: '#ECFDF5',
                                                    color: '#059669',
                                                    borderRadius: '99px',
                                                    fontSize: '13px',
                                                    fontWeight: '600'
                                                }}>
                                                    {job.successful}
                                                </span>
                                            </td>
                                            <td style={{ padding: '16px 24px' }}>
                                                {job.failed > 0 ? (
                                                    <span style={{
                                                        padding: '4px 10px',
                                                        backgroundColor: '#FEE2E2',
                                                        color: '#DC2626',
                                                        borderRadius: '99px',
                                                        fontSize: '13px',
                                                        fontWeight: '600'
                                                    }}>
                                                        {job.failed}
                                                    </span>
                                                ) : (
                                                    <span style={{ color: '#9CA3AF' }}>0</span>
                                                )}
                                            </td>
                                            <td style={{ padding: '16px 24px', color: '#6B7280', fontSize: '14px' }}>
                                                {job.created_by}
                                            </td>
                                            <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                                                <ActionMenu
                                                    actions={[
                                                        {
                                                            label: 'Download Results',
                                                            icon: '📥',
                                                            onClick: async () => {
                                                                try {
                                                                    const blob = await invitationApi.downloadBulkResults(job.job_id);
                                                                    const url = window.URL.createObjectURL(blob);
                                                                    const a = document.createElement('a');
                                                                    a.href = url;
                                                                    a.download = `bulk_results_${job.job_id.slice(0, 8)}.csv`;
                                                                    document.body.appendChild(a);
                                                                    a.click();
                                                                    document.body.removeChild(a);
                                                                } catch (err) {
                                                                    setError('Failed to download results');
                                                                }
                                                            }
                                                        },
                                                        ...(job.failed > 0 ? [{
                                                            label: 'Download Failures',
                                                            icon: '⚠️',
                                                            onClick: async () => {
                                                                try {
                                                                    const blob = await invitationApi.downloadBulkFailures(job.job_id);
                                                                    const url = window.URL.createObjectURL(blob);
                                                                    const a = document.createElement('a');
                                                                    a.href = url;
                                                                    a.download = `bulk_failures_${job.job_id.slice(0, 8)}.csv`;
                                                                    document.body.appendChild(a);
                                                                    a.click();
                                                                    document.body.removeChild(a);
                                                                } catch (err) {
                                                                    setError('Failed to download failures');
                                                                }
                                                            }
                                                        }] : [])
                                                    ]}
                                                />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {bulkJobs.length === 0 && (
                                <div style={{ padding: '60px 24px', textAlign: 'center', color: '#9CA3AF' }}>
                                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
                                    <div style={{ fontWeight: '600', marginBottom: '8px' }}>No bulk invite history</div>
                                    <div style={{ fontSize: '14px' }}>Upload a CSV file to invite multiple users at once</div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Bulk Invite Modal */}
                <BulkInviteModal
                    isOpen={showBulkInviteModal}
                    onClose={() => setShowBulkInviteModal(false)}
                    onSuccess={() => {
                        loadData();
                        setSuccess('Bulk invitations processed successfully!');
                    }}
                />

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
                                        name="email"
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
                                            if (!teamId) setSelectedTeamRole('team_contributor');
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
                                            <option value="team_contributor">Team Contributor</option>
                                            <option value="team_manager">Team Manager</option>
                                            <option value="team_reader">Team Reader</option>
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

                                {/* Restricted Invite Note logic (optional, removing Field Manager specific) */}
                                {false && (
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
                                    >
                                        📨 Send Invitation
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>

            {/* Edit User Modal */}
            {showEditUserModal && editingUser && (
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
                }} onClick={() => setShowEditUserModal(false)}>
                    <div style={{
                        width: '100%',
                        maxWidth: '520px',
                        background: 'white',
                        borderRadius: '16px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                        overflow: 'hidden'
                    }} onClick={(e) => e.stopPropagation()}>
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
                                <span style={{ fontSize: '28px' }}>✏️</span>
                                Edit User Role
                            </h2>
                            <p style={{ margin: '8px 0 0 0', fontSize: '14px', opacity: 0.9 }}>
                                Update role for {editingUser.name || editingUser.email}
                            </p>
                        </div>

                        <form onSubmit={handleUpdateUserRole} style={{ padding: '28px' }}>
                            <div style={{ marginBottom: '28px' }}>
                                <label style={{
                                    display: 'block',
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    fontSize: '14px',
                                    color: '#374151'
                                }}>
                                    Role
                                </label>
                                <select
                                    value={newRole}
                                    onChange={(e) => setNewRole(e.target.value)}
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
                                >
                                    {availableRoles.map(role => (
                                        <option key={role.value} value={role.value} disabled={role.disabled}>
                                            {role.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                                <button
                                    type="button"
                                    onClick={() => setShowEditUserModal(false)}
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
                                    disabled={loading}
                                    style={{
                                        padding: '12px 24px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: 'pointer',
                                        boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
                                        transition: 'all 0.2s',
                                        opacity: loading ? 0.7 : 1
                                    }}
                                >
                                    {loading ? 'Saving...' : 'Save Changes'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </AdminLayout>
    );
};

export default InvitationsPage;
