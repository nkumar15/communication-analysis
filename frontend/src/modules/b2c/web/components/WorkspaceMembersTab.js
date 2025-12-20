import React, { useState } from 'react';
import b2cWorkspaceClient from '../../../../core/api/b2cWorkspaceClient';

const WorkspaceMembersTab = ({ workspace, members, onMembersUpdated }) => {
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState('member');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [invitations, setInvitations] = useState([]);

    // Fetch invitations on mount
    React.useEffect(() => {
        if (workspace?.id) {
            loadInvitations();
        }
    }, [workspace?.id]);

    const loadInvitations = async () => {
        try {
            const data = await b2cWorkspaceClient.getWorkspaceInvitations(workspace.id);
            setInvitations(data.invitations || []);
        } catch (err) {
            console.error('Failed to load invitations:', err);
        }
    };

    const handleInviteMember = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            await b2cWorkspaceClient.inviteToWorkspace(workspace.id, inviteEmail, inviteRole);
            setShowInviteModal(false);
            setInviteEmail('');
            setInviteRole('member');
            alert('Invitation sent successfully!');
            loadInvitations(); // Reload invitations
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateRole = async (userId, newRole) => {
        try {
            await b2cWorkspaceClient.updateMemberRole(workspace.id, userId, newRole);
            onMembersUpdated();
            alert('Role updated successfully');
        } catch (err) {
            alert(`Failed to update role: ${err.message}`);
        }
    };

    const handleToggleStatus = async (userId, currentStatus) => {
        const newStatus = currentStatus === 'active' ? 'suspended' : 'active';
        const action = newStatus === 'active' ? 'activate' : 'deactivate';

        if (!confirm(`Are you sure you want to ${action} this member?`)) return;

        try {
            await b2cWorkspaceClient.updateMemberStatus(workspace.id, userId, newStatus);
            onMembersUpdated();
            alert(`Member ${action}d successfully`);
        } catch (err) {
            alert(`Failed to update status: ${err.message}`);
        }
    };

    const handleRemoveMember = async (userId) => {
        if (!confirm('Are you sure you want to remove this member?')) return;

        try {
            await b2cWorkspaceClient.removeMember(workspace.id, userId);
            onMembersUpdated();
            alert('Member removed successfully');
        } catch (err) {
            alert(`Failed to remove member: ${err.message}`);
        }
    };

    const handleResendInvitation = async (invitationId) => {
        try {
            await b2cWorkspaceClient.resendInvitation(invitationId);
            alert('Invitation resent successfully');
        } catch (err) {
            alert(`Failed to resend invitation: ${err.message}`);
        }
    };

    const handleCancelInvitation = async (invitationId) => {
        if (!confirm('Are you sure you want to cancel this invitation?')) return;

        try {
            await b2cWorkspaceClient.cancelInvitation(invitationId);
            loadInvitations();
            alert('Invitation cancelled successfully');
        } catch (err) {
            alert(`Failed to cancel invitation: ${err.message}`);
        }
    };

    return (
        <div>
            {/* Header with Invite Button */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Workspace Members</h3>
                {workspace.type === 'team' && (
                    <button
                        onClick={() => setShowInviteModal(true)}
                        style={{
                            padding: '10px 20px',
                            borderRadius: '8px',
                            border: 'none',
                            background: '#6366F1',
                            color: 'white',
                            fontSize: '14px',
                            fontWeight: '600',
                            cursor: 'pointer'
                        }}
                    >
                        ✉️ Invite Member
                    </button>
                )}
            </div>

            {/* Pending Invitations Section */}
            {invitations.length > 0 && (
                <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#6B7280', marginBottom: '16px', textTransform: 'uppercase' }}>
                        Pending Invitations
                    </h4>
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        border: '1px solid #E5E7EB',
                        overflow: 'hidden'
                    }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Email</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Role</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Sent</th>
                                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {invitations.map((invitation) => (
                                    <tr key={invitation.id} style={{ borderBottom: '1px solid #E5E7EB' }}>
                                        <td style={{ padding: '16px', fontWeight: '500', color: '#111827' }}>
                                            {invitation.email}
                                        </td>
                                        <td style={{ padding: '16px' }}>
                                            <span style={{
                                                padding: '4px 12px',
                                                borderRadius: '9999px',
                                                fontSize: '12px',
                                                fontWeight: '600',
                                                backgroundColor: '#F3F4F6',
                                                color: '#374151'
                                            }}>
                                                {invitation.role}
                                            </span>
                                        </td>
                                        <td style={{ padding: '16px', fontSize: '14px', color: '#6B7280' }}>
                                            {new Date(invitation.created_at).toLocaleDateString()}
                                        </td>
                                        <td style={{ padding: '16px' }}>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                <button
                                                    onClick={() => handleResendInvitation(invitation.id)}
                                                    style={{
                                                        padding: '6px 12px',
                                                        borderRadius: '6px',
                                                        border: '1px solid #E5E7EB',
                                                        backgroundColor: 'white',
                                                        color: '#6366F1',
                                                        fontSize: '13px',
                                                        fontWeight: '500',
                                                        cursor: 'pointer'
                                                    }}
                                                >
                                                    Resend
                                                </button>
                                                <button
                                                    onClick={() => handleCancelInvitation(invitation.id)}
                                                    style={{
                                                        padding: '6px 12px',
                                                        borderRadius: '6px',
                                                        border: '1px solid #EF4444',
                                                        backgroundColor: 'white',
                                                        color: '#EF4444',
                                                        fontSize: '13px',
                                                        fontWeight: '500',
                                                        cursor: 'pointer'
                                                    }}
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Members Table */}
            <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#6B7280', marginBottom: '16px', textTransform: 'uppercase' }}>
                Active Members
            </h4>
            <div style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                border: '1px solid #E5E7EB',
                overflow: 'hidden'
            }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Member</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Status</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Role</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Joined</th>
                            <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: '600', color: '#6B7280' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {members.map((member) => (
                            <tr key={member.user_id} style={{ borderBottom: '1px solid #E5E7EB', opacity: member.status === 'suspended' ? 0.6 : 1 }}>
                                <td style={{ padding: '16px' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span style={{ fontWeight: '500', color: '#111827' }}>{member.email || member.display_name}</span>
                                        {member.email && member.display_name && (
                                            <span style={{ fontSize: '12px', color: '#6B7280' }}>{member.display_name}</span>
                                        )}
                                    </div>
                                </td>
                                <td style={{ padding: '16px' }}>
                                    <span style={{
                                        padding: '4px 12px',
                                        borderRadius: '9999px',
                                        fontSize: '12px',
                                        fontWeight: '600',
                                        backgroundColor: member.status === 'suspended' ? '#FEE2E2' : '#D1FAE5',
                                        color: member.status === 'suspended' ? '#DC2626' : '#059669'
                                    }}>
                                        {member.status || 'active'}
                                    </span>
                                </td>
                                <td style={{ padding: '16px' }}>
                                    <span style={{
                                        padding: '4px 12px',
                                        borderRadius: '9999px',
                                        fontSize: '12px',
                                        fontWeight: '600',
                                        backgroundColor: member.role === 'owner' ? '#7C3AED20' : member.role === 'admin' ? '#DC262620' : '#6366F120',
                                        color: member.role === 'owner' ? '#7C3AED' : member.role === 'admin' ? '#DC2626' : '#6366F1'
                                    }}>
                                        {member.role}
                                    </span>
                                </td>
                                <td style={{ padding: '16px', fontSize: '14px', color: '#6B7280' }}>
                                    {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : 'N/A'}
                                </td>
                                <td style={{ padding: '16px' }}>
                                    {member.role !== 'owner' && (
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            <select
                                                value={member.role}
                                                onChange={(e) => handleUpdateRole(member.user_id, e.target.value)}
                                                style={{
                                                    padding: '6px 12px',
                                                    borderRadius: '6px',
                                                    border: '1px solid #E5E7EB',
                                                    fontSize: '13px',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                <option value="admin">Admin</option>
                                                <option value="member">Member</option>
                                                <option value="viewer">Viewer</option>
                                            </select>

                                            <button
                                                onClick={() => handleToggleStatus(member.user_id, member.status)}
                                                style={{
                                                    padding: '6px 12px',
                                                    borderRadius: '6px',
                                                    border: '1px solid #E5E7EB',
                                                    backgroundColor: 'white',
                                                    color: member.status === 'suspended' ? '#059669' : '#D97706',
                                                    fontSize: '13px',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                {member.status === 'suspended' ? 'Activate' : 'Suspend'}
                                            </button>

                                            <button
                                                onClick={() => handleRemoveMember(member.user_id)}
                                                style={{
                                                    padding: '6px 12px',
                                                    borderRadius: '6px',
                                                    border: '1px solid #EF4444',
                                                    backgroundColor: 'white',
                                                    color: '#EF4444',
                                                    fontSize: '13px',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                Remove
                                            </button>
                                        </div>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
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
                    zIndex: 1000
                }}>
                    <div style={{
                        backgroundColor: 'white',
                        borderRadius: '16px',
                        padding: '32px',
                        maxWidth: '500px',
                        width: '90%'
                    }}>
                        <h2 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '8px' }}>Invite Member</h2>
                        <p style={{ color: '#6B7280', marginBottom: '24px' }}>Send an invitation to join {workspace.name}</p>

                        <form onSubmit={handleInviteMember}>
                            <div style={{ marginBottom: '20px' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    value={inviteEmail}
                                    onChange={(e) => setInviteEmail(e.target.value)}
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '12px',
                                        borderRadius: '8px',
                                        border: '1px solid #E5E7EB',
                                        fontSize: '14px'
                                    }}
                                    placeholder="colleague@example.com"
                                />
                            </div>

                            <div style={{ marginBottom: '24px' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', fontSize: '14px' }}>
                                    Role
                                </label>
                                <select
                                    value={inviteRole}
                                    onChange={(e) => setInviteRole(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '12px',
                                        borderRadius: '8px',
                                        border: '1px solid #E5E7EB',
                                        fontSize: '14px'
                                    }}
                                >
                                    <option value="admin">Admin</option>
                                    <option value="member">Member</option>
                                    <option value="viewer">Viewer</option>
                                </select>
                            </div>

                            {error && (
                                <div style={{
                                    padding: '12px',
                                    borderRadius: '8px',
                                    backgroundColor: '#FEE2E2',
                                    color: '#EF4444',
                                    marginBottom: '20px',
                                    fontSize: '14px'
                                }}>
                                    {error}
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                                <button
                                    type="button"
                                    onClick={() => setShowInviteModal(false)}
                                    style={{
                                        padding: '10px 20px',
                                        borderRadius: '8px',
                                        border: '1px solid #E5E7EB',
                                        backgroundColor: 'white',
                                        color: '#6B7280',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    style={{
                                        padding: '10px 20px',
                                        borderRadius: '8px',
                                        border: 'none',
                                        background: '#6366F1',
                                        color: 'white',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        cursor: loading ? 'not-allowed' : 'pointer',
                                        opacity: loading ? 0.6 : 1
                                    }}
                                >
                                    {loading ? 'Sending...' : 'Send Invitation'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default WorkspaceMembersTab;
