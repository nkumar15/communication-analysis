import React, { useState, useEffect } from 'react';
import api from '../../../core/api/platformClient';

const UsersPage = () => {
    const [invitations, setInvitations] = useState([]);
    const [roles, setRoles] = useState([]);
    const [activeTab, setActiveTab] = useState('invitations');
    const [loading, setLoading] = useState(true);
    const [showInviteModal, setShowInviteModal] = useState(false);

    // Invite Form State
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRoleId, setInviteRoleId] = useState('');
    const [inviteLoading, setInviteLoading] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [invitesRes, rolesRes] = await Promise.all([
                api.get('/api/platform/invitations/'),
                api.get('/api/platform/roles/')
            ]);
            setInvitations(invitesRes);
            setRoles(rolesRes);
        } catch (error) {
            console.error("Failed to load users/invitations", error);
        } finally {
            setLoading(false);
        }
    };

    const handleInvite = async (e) => {
        e.preventDefault();
        setInviteLoading(true);
        try {
            await api.post('/api/platform/invitations/', {
                email: inviteEmail,
                role_id: inviteRoleId
            });
            setShowInviteModal(false);
            setInviteEmail('');
            setInviteRoleId('');
            fetchData();
            alert('Invitation sent successfully!');
        } catch (error) {
            alert('Failed to send invitation: ' + (error.response?.data?.detail || error.message));
        } finally {
            setInviteLoading(false);
        }
    };

    const handleRevoke = async (inviteId) => {
        if (!window.confirm("Are you sure you want to revoke this invitation?")) return;
        try {
            await api.post(`/api/platform/invitations/${inviteId}/revoke`);
            fetchData();
        } catch (error) {
            alert('Failed to revoke: ' + error.message);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'pending': return { bg: '#FEF3C7', color: '#D97706' };
            case 'accepted': return { bg: '#D1FAE5', color: '#059669' };
            case 'expired': return { bg: '#FEE2E2', color: '#DC2626' };
            case 'revoked': return { bg: '#F3F4F6', color: '#6B7280' };
            default: return { bg: '#F3F4F6', color: '#6B7280' };
        }
    };

    if (loading && !showInviteModal) {
        return (
            <div className="p-10">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
                    <div className="bg-white rounded-lg shadow">
                        <div className="h-64 bg-gray-100"></div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div style={{ padding: '2.5rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <div>
                    <h1 style={{
                        fontSize: '24px',
                        fontWeight: 600,
                        color: '#111827',
                        marginBottom: '4px'
                    }}>
                        Platform Users
                    </h1>
                    <p style={{ fontSize: '14px', color: '#6B7280' }}>
                        Manage platform administrators and invitations
                    </p>
                </div>
                <button
                    onClick={() => setShowInviteModal(true)}
                    style={{
                        backgroundColor: '#8B5CF6',
                        color: '#FFFFFF',
                        padding: '12px 20px',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: 500,
                        cursor: 'pointer',
                        border: 'none',
                        transition: 'background-color 0.15s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#7C3AED'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#8B5CF6'}
                >
                    + Invite User
                </button>
            </div>

            {/* Tabs */}
            <div style={{ borderBottom: '1px solid #E5E7EB', marginBottom: '24px' }}>
                <nav style={{ display: 'flex', gap: '32px' }}>
                    <button
                        onClick={() => setActiveTab('users')}
                        disabled
                        style={{
                            padding: '16px 4px',
                            borderBottom: activeTab === 'users' ? '2px solid #8B5CF6' : '2px solid transparent',
                            color: activeTab === 'users' ? '#8B5CF6' : '#9CA3AF',
                            fontSize: '14px',
                            fontWeight: 500,
                            background: 'none',
                            border: 'none',
                            borderBottom: activeTab === 'users' ? '2px solid #8B5CF6' : '2px solid transparent',
                            cursor: 'not-allowed',
                            opacity: 0.5,
                            transition: 'color 0.15s ease'
                        }}
                    >
                        Active Users (Coming Soon)
                    </button>
                    <button
                        onClick={() => setActiveTab('invitations')}
                        style={{
                            padding: '16px 4px',
                            borderBottom: activeTab === 'invitations' ? '2px solid #8B5CF6' : '2px solid transparent',
                            color: activeTab === 'invitations' ? '#8B5CF6' : '#6B7280',
                            fontSize: '14px',
                            fontWeight: 500,
                            background: 'none',
                            border: 'none',
                            borderBottom: activeTab === 'invitations' ? '2px solid #8B5CF6' : '2px solid transparent',
                            cursor: 'pointer',
                            transition: 'color 0.15s ease'
                        }}
                    >
                        Invitations ({invitations.length})
                    </button>
                </nav>
            </div>

            {/* Content */}
            {activeTab === 'invitations' && (
                <div style={{ backgroundColor: '#FFFFFF', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
                    {invitations.length === 0 ? (
                        <div style={{ padding: '48px 24px', textAlign: 'center', color: '#9CA3AF' }}>
                            No invitations found.
                        </div>
                    ) : (
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                            {invitations.map((invite, index) => {
                                const statusStyle = getStatusColor(invite.status);
                                return (
                                    <li
                                        key={invite.id}
                                        style={{
                                            padding: '20px 24px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            borderBottom: index < invitations.length - 1 ? '1px solid #F3F4F6' : 'none',
                                            transition: 'background-color 0.15s ease'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F9FAFB'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                    >
                                        <div>
                                            <div style={{ fontSize: '14px', fontWeight: 500, color: '#8B5CF6', marginBottom: '4px' }}>
                                                {invite.email}
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#6B7280' }}>
                                                <span>Role: {invite.role_name}</span>
                                                <span>•</span>
                                                <span style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    padding: '2px 8px',
                                                    borderRadius: '12px',
                                                    fontSize: '11px',
                                                    fontWeight: 500,
                                                    backgroundColor: statusStyle.bg,
                                                    color: statusStyle.color
                                                }}>
                                                    {invite.status}
                                                </span>
                                            </div>
                                            <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
                                                Expires: {new Date(invite.expires_at).toLocaleDateString()}
                                            </div>
                                        </div>
                                        <div>
                                            {invite.status === 'pending' && (
                                                <button
                                                    onClick={() => handleRevoke(invite.id)}
                                                    style={{
                                                        color: '#DC2626',
                                                        fontSize: '14px',
                                                        fontWeight: 500,
                                                        background: 'none',
                                                        border: 'none',
                                                        cursor: 'pointer',
                                                        padding: '8px 12px',
                                                        transition: 'color 0.15s ease'
                                                    }}
                                                    onMouseEnter={(e) => e.currentTarget.style.color = '#991B1B'}
                                                    onMouseLeave={(e) => e.currentTarget.style.color = '#DC2626'}
                                                >
                                                    Revoke
                                                </button>
                                            )}
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </div>
            )}

            {/* Stats Footer */}
            {activeTab === 'invitations' && (
                <div style={{ marginTop: '16px', fontSize: '12px', color: '#6B7280' }}>
                    Showing {invitations.length} invitation{invitations.length !== 1 ? 's' : ''}
                </div>
            )}

            {/* Invite Modal */}
            {showInviteModal && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 50
                }}>
                    <div style={{
                        backgroundColor: '#FFFFFF',
                        borderRadius: '12px',
                        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
                        padding: '32px',
                        maxWidth: '480px',
                        width: '100%'
                    }}>
                        <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#111827', marginBottom: '24px' }}>
                            Invite Platform User
                        </h3>

                        <form onSubmit={handleInvite}>
                            <div style={{ marginBottom: '20px' }}>
                                <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, color: '#374151', marginBottom: '8px' }}>
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        color: '#111827'
                                    }}
                                    value={inviteEmail}
                                    onChange={(e) => setInviteEmail(e.target.value)}
                                />
                            </div>

                            <div style={{ marginBottom: '24px' }}>
                                <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, color: '#374151', marginBottom: '8px' }}>
                                    Role
                                </label>
                                <select
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        color: '#111827',
                                        backgroundColor: '#FFFFFF'
                                    }}
                                    value={inviteRoleId}
                                    onChange={(e) => setInviteRoleId(e.target.value)}
                                >
                                    <option value="">Select a role...</option>
                                    {roles.map(r => (
                                        <option key={r.id} value={r.id}>{r.display_name}</option>
                                    ))}
                                </select>
                            </div>

                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                                <button
                                    type="button"
                                    onClick={() => setShowInviteModal(false)}
                                    style={{
                                        padding: '10px 20px',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        fontWeight: 500,
                                        backgroundColor: '#F3F4F6',
                                        color: '#374151',
                                        border: 'none',
                                        cursor: 'pointer',
                                        transition: 'background-color 0.15s ease'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#E5E7EB'}
                                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#F3F4F6'}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={inviteLoading}
                                    style={{
                                        padding: '10px 20px',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        fontWeight: 500,
                                        backgroundColor: inviteLoading ? '#D8B4FE' : '#8B5CF6',
                                        color: '#FFFFFF',
                                        border: 'none',
                                        cursor: inviteLoading ? 'not-allowed' : 'pointer',
                                        transition: 'background-color 0.15s ease'
                                    }}
                                    onMouseEnter={(e) => !inviteLoading && (e.currentTarget.style.backgroundColor = '#7C3AED')}
                                    onMouseLeave={(e) => !inviteLoading && (e.currentTarget.style.backgroundColor = '#8B5CF6')}
                                >
                                    {inviteLoading ? 'Sending...' : 'Send Invite'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UsersPage;
