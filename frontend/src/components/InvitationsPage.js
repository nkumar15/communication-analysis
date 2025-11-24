import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import invitationApi from '../services/invitationApi';
import './Card.css';
import './Button.css';

const InvitationsPage = () => {
    const [invitations, setInvitations] = useState([]);
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    // Load invitations on mount
    useEffect(() => {
        loadInvitations();
    }, []);

    const loadInvitations = async () => {
        try {
            const data = await invitationApi.listInvitations();
            setInvitations(data);
        } catch (err) {
            console.error('Failed to load invitations:', err);
            if (err.response?.status === 403) {
                setError('Only admins can view invitations');
            }
        }
    };

    const handleInvite = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setLoading(true);

        try {
            const result = await invitationApi.inviteUser(email, 'manager');
            setSuccess(result.message);
            setEmail('');
            await loadInvitations(); // Reload list
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to send invitation');
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async (invitationId) => {
        try {
            const result = await invitationApi.resendInvitation(invitationId);
            setSuccess(result.message);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to resend invitation');
        }
    };

    const handleCancel = async (invitationId) => {
        if (!window.confirm('Are you sure you want to cancel this invitation?')) {
            return;
        }

        try {
            await invitationApi.cancelInvitation(invitationId);
            setSuccess('Invitation cancelled');
            await loadInvitations();
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to cancel invitation');
        }
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const isPending = (invitation) => !invitation.accepted_at;
    const isExpired = (invitation) => new Date(invitation.expires_at) < new Date();

    return (
        <div style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ margin: 0 }}>Team Invitations</h1>
                <button
                    onClick={() => navigate('/dashboard')}
                    className="button button-secondary"
                >
                    ← Back to Dashboard
                </button>
            </div>

            {/* Invite Form */}
            <div className="card" style={{ marginBottom: '30px' }}>
                <h2 style={{ marginTop: 0 }}>Invite Manager</h2>

                {error && (
                    <div style={{
                        padding: '12px',
                        backgroundColor: '#fee',
                        border: '1px solid #fcc',
                        borderRadius: '6px',
                        marginBottom: '20px',
                        color: '#c33'
                    }}>
                        {error}
                    </div>
                )}

                {success && (
                    <div style={{
                        padding: '12px',
                        backgroundColor: '#efe',
                        border: '1px solid #cfc',
                        borderRadius: '6px',
                        marginBottom: '20px',
                        color: '#3c3'
                    }}>
                        {success}
                    </div>
                )}

                <form onSubmit={handleInvite}>
                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
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
                                border: '1px solid #ddd',
                                borderRadius: '6px',
                                fontSize: '16px'
                            }}
                        />
                        <small style={{ color: '#666', display: 'block', marginTop: '6px' }}>
                            Email must match your company domain
                        </small>
                    </div>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                            Role
                        </label>
                        <input
                            type="text"
                            value="Manager"
                            disabled
                            style={{
                                width: '100%',
                                padding: '12px',
                                border: '1px solid #ddd',
                                borderRadius: '6px',
                                fontSize: '16px',
                                backgroundColor: '#f5f5f5'
                            }}
                        />
                        <small style={{ color: '#666', display: 'block', marginTop: '6px' }}>
                            Currently only manager role is available
                        </small>
                    </div>

                    <button
                        type="submit"
                        disabled={loading || !email}
                        className="button button-primary"
                        style={{ width: '100%' }}
                    >
                        {loading ? 'Sending...' : 'Send Invitation'}
                    </button>
                </form>
            </div>

            {/* Invitations List */}
            <div className="card">
                <h2 style={{ marginTop: 0 }}>Invitations</h2>

                {invitations.length === 0 ? (
                    <p style={{ color: '#666', textAlign: 'center', padding: '40px' }}>
                        No invitations yet. Invite your first team member above!
                    </p>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid #ddd' }}>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Email</th>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Role</th>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Status</th>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Sent</th>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Expires</th>
                                    <th style={{ padding: '12px', textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {invitations.map((inv) => (
                                    <tr key={inv.id} style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '12px' }}>{inv.email}</td>
                                        <td style={{ padding: '12px' }}>
                                            <span style={{
                                                padding: '4px 8px',
                                                backgroundColor: '#e0e7ff',
                                                color: '#4338ca',
                                                borderRadius: '4px',
                                                fontSize: '14px'
                                            }}>
                                                {inv.role}
                                            </span>
                                        </td>
                                        <td style={{ padding: '12px' }}>
                                            {inv.accepted_at ? (
                                                <span style={{ color: '#16a34a', fontWeight: '500' }}>
                                                    ✓ Accepted
                                                </span>
                                            ) : isExpired(inv) ? (
                                                <span style={{ color: '#dc2626', fontWeight: '500' }}>
                                                    ⚠ Expired
                                                </span>
                                            ) : (
                                                <span style={{ color: '#ea580c', fontWeight: '500' }}>
                                                    ⏳ Pending
                                                </span>
                                            )}
                                        </td>
                                        <td style={{ padding: '12px', fontSize: '14px', color: '#666' }}>
                                            {formatDate(inv.created_at)}
                                        </td>
                                        <td style={{ padding: '12px', fontSize: '14px', color: '#666' }}>
                                            {formatDate(inv.expires_at)}
                                        </td>
                                        <td style={{ padding: '12px', textAlign: 'right' }}>
                                            {isPending(inv) && (
                                                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                                                    <button
                                                        onClick={() => handleResend(inv.id)}
                                                        className="button button-secondary"
                                                        style={{ fontSize: '14px', padding: '6px 12px' }}
                                                    >
                                                        Resend
                                                    </button>
                                                    <button
                                                        onClick={() => handleCancel(inv.id)}
                                                        className="button"
                                                        style={{
                                                            fontSize: '14px',
                                                            padding: '6px 12px',
                                                            backgroundColor: '#fee',
                                                            color: '#c33',
                                                            border: '1px solid #fcc'
                                                        }}
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default InvitationsPage;
