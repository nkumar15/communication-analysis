import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { auth } from '../../../../core/firebase/b2c-config';
import b2cWorkspaceClient from '../../../../core/api/b2cWorkspaceClient';

const InvitationAcceptPage = () => {
    const { token } = useParams();
    const navigate = useNavigate();
    const [invitation, setInvitation] = useState(null);
    const [loading, setLoading] = useState(true);
    const [accepting, setAccepting] = useState(false);
    const [error, setError] = useState('');
    const [requiresLogin, setRequiresLogin] = useState(false);

    useEffect(() => {
        loadInvitation();
    }, [token]);

    const loadInvitation = async () => {
        setLoading(true);
        setError('');

        try {
            // Check if user is authenticated
            const user = auth.currentUser;
            if (!user) {
                setRequiresLogin(true);
            }

            // Get invitation details (public endpoint)
            const data = await b2cWorkspaceClient.getInvitation(token);
            setInvitation(data);
        } catch (err) {
            setError(err.message || 'Invalid or expired invitation');
        } finally {
            setLoading(false);
        }
    };

    const handleAcceptInvitation = async () => {
        // Check if user is authenticated
        const user = auth.currentUser;
        if (!user) {
            // Redirect to login with return URL and pre-fill email
            localStorage.setItem('invitation_return_token', token);
            navigate(`/login?email=${encodeURIComponent(invitation.email)}`);
            return;
        }

        setAccepting(true);
        setError('');

        try {
            await b2cWorkspaceClient.acceptInvitation(token);
            alert('Successfully joined workspace!');
            navigate('/workspaces');
        } catch (err) {
            setError(err.message || 'Failed to accept invitation');
        } finally {
            setAccepting(false);
        }
    };

    if (loading) {
        return (
            <div style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#F9FAFB'
            }}>
                <div style={{ fontSize: '48px' }}>⏳</div>
            </div>
        );
    }

    if (error && !invitation) {
        return (
            <div style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#F9FAFB',
                padding: '24px'
            }}>
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '16px',
                    padding: '48px',
                    maxWidth: '500px',
                    width: '100%',
                    textAlign: 'center',
                    border: '1px solid #E5E7EB'
                }}>
                    <div style={{ fontSize: '64px', marginBottom: '24px' }}>❌</div>
                    <h1 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '12px', color: '#111827' }}>
                        Invalid Invitation
                    </h1>
                    <p style={{ color: '#6B7280', marginBottom: '32px' }}>
                        {error}
                    </p>
                    <button
                        onClick={() => navigate('/')}
                        style={{
                            padding: '12px 24px',
                            borderRadius: '10px',
                            border: 'none',
                            background: '#6366F1',
                            color: 'white',
                            fontSize: '14px',
                            fontWeight: '600',
                            cursor: 'pointer'
                        }}
                    >
                        Go to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#F9FAFB',
            padding: '24px'
        }}>
            <div style={{
                backgroundColor: 'white',
                borderRadius: '16px',
                padding: '48px',
                maxWidth: '600px',
                width: '100%',
                border: '1px solid #E5E7EB'
            }}>
                {/* Header */}
                <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                    <div style={{ fontSize: '64px', marginBottom: '24px' }}>🎉</div>
                    <h1 style={{ fontSize: '28px', fontWeight: '700', marginBottom: '12px', color: '#111827' }}>
                        You're Invited!
                    </h1>
                    <p style={{ fontSize: '16px', color: '#6B7280' }}>
                        {invitation?.inviter?.display_name || invitation?.inviter?.email} has invited you to join
                    </p>
                </div>

                {/* Workspace Info */}
                <div style={{
                    backgroundColor: '#F9FAFB',
                    borderRadius: '12px',
                    padding: '24px',
                    marginBottom: '32px'
                }}>
                    <div style={{ marginBottom: '16px' }}>
                        <div style={{ fontSize: '12px', color: '#6B7280', textTransform: 'uppercase', marginBottom: '4px', fontWeight: '600' }}>
                            Workspace
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: '700', color: '#111827' }}>
                            {invitation?.workspace?.name}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '12px', color: '#6B7280', textTransform: 'uppercase', marginBottom: '4px', fontWeight: '600' }}>
                            Your Role
                        </div>
                        <span style={{
                            padding: '6px 16px',
                            borderRadius: '9999px',
                            fontSize: '14px',
                            fontWeight: '600',
                            backgroundColor: invitation?.role === 'admin' ? '#DC262620' : '#6366F120',
                            color: invitation?.role === 'admin' ? '#DC2626' : '#6366F1',
                            display: 'inline-block'
                        }}>
                            {invitation?.role}
                        </span>
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div style={{
                        padding: '16px',
                        borderRadius: '8px',
                        backgroundColor: '#FEE2E2',
                        color: '#EF4444',
                        marginBottom: '24px',
                        fontSize: '14px'
                    }}>
                        {error}
                    </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <button
                        onClick={handleAcceptInvitation}
                        disabled={accepting}
                        style={{
                            padding: '16px 24px',
                            borderRadius: '10px',
                            border: 'none',
                            background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
                            color: 'white',
                            fontSize: '16px',
                            fontWeight: '600',
                            cursor: accepting ? 'not-allowed' : 'pointer',
                            opacity: accepting ? 0.6 : 1,
                            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)'
                        }}
                    >
                        {accepting ? 'Accepting...' : requiresLogin ? 'Login to Accept' : 'Accept Invitation'}
                    </button>
                    <button
                        onClick={() => navigate('/')}
                        style={{
                            padding: '12px 24px',
                            borderRadius: '10px',
                            border: '1px solid #E5E7EB',
                            backgroundColor: 'white',
                            color: '#6B7280',
                            fontSize: '14px',
                            fontWeight: '600',
                            cursor: 'pointer'
                        }}
                    >
                        Maybe Later
                    </button>
                </div>

                {/* Expiry Notice */}
                <p style={{ textAlign: 'center', fontSize: '12px', color: '#9CA3AF', marginTop: '24px' }}>
                    This invitation expires {invitation?.expires_at && new Date(invitation.expires_at).toLocaleDateString()}
                </p>
            </div>
        </div>
    );
};

export default InvitationAcceptPage;
