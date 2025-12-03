import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import invitationApi from '../../../core/api/invitationClient';
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
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
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

    const [selectedRole, setSelectedRole] = useState('field_manager'); // default role
    const [selectedTeam, setSelectedTeam] = useState('');
    const handleInvite = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        try {
            // Send the selected role directly (new role names)
            await invitationApi.inviteUser(email, selectedRole, selectedTeam || null);
            setSuccess(`Invitation sent to ${email}`);
            setEmail('');
            setSelectedTeam('');
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
                        backgroundColor: 'rgba(0, 0, 0, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 100
                    }} onClick={() => setShowInviteModal(false)}>
                        <div className="card" style={{ width: '100%', maxWidth: '500px', margin: '20px' }} onClick={(e) => e.stopPropagation()}>
                            <h2 style={{ marginTop: 0 }}>Invite User</h2>
                            <form onSubmit={handleInvite}>
                                <div style={{ marginBottom: '20px' }}>
                                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                                        Email Address
                                    </label>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="manager@yourcompany.com"
                                        required
                                        style={{
                                            width: '100%',
                                            padding: '12px',
                                            border: '1px solid #D1D5DB',
                                            borderRadius: '6px',
                                            fontSize: '14px'
                                        }}
                                    />
                                    <small style={{ color: '#6B7280', fontSize: '13px', display: 'block', marginTop: '6px' }}>
                                        Email must match your company domain
                                    </small>
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500', color: '#374151' }}>
                                        Role
                                    </label>
                                    <select
                                        value={selectedRole}
                                        onChange={(e) => setSelectedRole(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '8px 12px',
                                            borderRadius: '6px',
                                            border: '1px solid #D1D5DB',
                                            fontSize: '14px'
                                        }}
                                    >
                                        {getInvitableRoles().map(role => (
                                            <option key={role.value} value={role.value}>
                                                {role.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div style={{ marginBottom: '24px' }}>
                                    <TeamSelector
                                        value={selectedTeam}
                                        onChange={setSelectedTeam}
                                        label="Assign to Team (Optional)"
                                    />
                                </div>

                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                                    {user?.role === 'field_manager' && (
                                        <small style={{ color: '#6B7280', fontSize: '12px', display: 'block', marginTop: '6px' }}>
                                            As a Field Manager, you can only invite Field Agents
                                        </small>
                                    )}
                                </div>
                                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                                    <button
                                        type="button"
                                        onClick={() => setShowInviteModal(false)}
                                        className="button button-secondary"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="button button-primary"
                                    >
                                        Send Invitation
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
