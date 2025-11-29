import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import invitationApi from '../../../core/api/invitationClient';
import firebaseAuthService from '../../../core/firebase/authService';

const InvitationAcceptPage = () => {
    const { token } = useParams();
    const navigate = useNavigate();

    const [loading, setLoading] = useState(true);
    const [invitation, setInvitation] = useState(null);
    const [error, setError] = useState('');
    const [ssoLoading, setSsoLoading] = useState(false);

    useEffect(() => {
        validateInvitation();
    }, [token]);

    const validateInvitation = async () => {
        try {
            const data = await invitationApi.validateInvitation(token);
            setInvitation(data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Invalid or expired invitation');
        } finally {
            setLoading(false);
        }
    };

    const handleAccept = async () => {
        setSsoLoading(true);
        setError('');

        try {
            // Set Firebase tenant context
            firebaseAuthService.setTenantId(invitation.firebase_tenant_id);

            // Initiate SSO login
            const result = await firebaseAuthService.signInWithOIDC(invitation.oidc_provider_id);

            if (result.user) {
                // User logged in successfully via SSO
                // Now join the tenant
                await invitationApi.joinTenant(token);

                // Redirect to dashboard
                navigate('/dashboard');
            }
        } catch (err) {
            console.error('SSO or join error:', err);
            setError(err.message || 'Failed to accept invitation');
            setSsoLoading(false);
        }
    };

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
                backgroundColor: '#f9fafb'
            }}>
                <div className="card" style={{ maxWidth: '500px', textAlign: 'center' }}>
                    <div style={{ fontSize: '48px', marginBottom: '20px' }}>⏳</div>
                    <h2>Validating invitation...</h2>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '100vh',
                backgroundColor: '#f9fafb'
            }}>
                <div className="card" style={{ maxWidth: '500px', textAlign: 'center' }}>
                    <div style={{ fontSize: '48px', marginBottom: '20px' }}>❌</div>
                    <h2>Invalid Invitation</h2>
                    <p style={{ color: '#666', marginBottom: '30px' }}>{error}</p>
                    <button
                        onClick={() => navigate('/login')}
                        className="button button-secondary"
                    >
                        Go to Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            backgroundColor: '#f9fafb',
            padding: '20px'
        }}>
            <div className="card" style={{ maxWidth: '600px', width: '100%' }}>
                <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                    <div style={{ fontSize: '64px', marginBottom: '20px' }}>📨</div>
                    <h1 style={{ marginBottom: '10px' }}>You're Invited!</h1>
                    <p style={{ color: '#666', fontSize: '18px' }}>
                        Join your team on Enterprise SSO
                    </p>
                </div>

                <div style={{
                    backgroundColor: '#f3f4f6',
                    padding: '24px',
                    borderRadius: '8px',
                    marginBottom: '30px'
                }}>
                    <div style={{ marginBottom: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                            Organization
                        </div>
                        <div style={{ fontSize: '20px', fontWeight: '600' }}>
                            {invitation.tenant_name}
                        </div>
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                            Invited by
                        </div>
                        <div style={{ fontSize: '16px' }}>
                            {invitation.inviter_name}
                        </div>
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                            Your role
                        </div>
                        <div>
                            <span style={{
                                display: 'inline-block',
                                padding: '6px 12px',
                                backgroundColor: '#e0e7ff',
                                color: '#4338ca',
                                borderRadius: '4px',
                                fontSize: '14px',
                                fontWeight: '500'
                            }}>
                                {invitation.role}
                            </span>
                        </div>
                    </div>

                    <div>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                            Email
                        </div>
                        <div style={{ fontSize: '16px' }}>
                            {invitation.email}
                        </div>
                    </div>
                </div>

                {ssoLoading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <div style={{ fontSize: '48px', marginBottom: '20px' }}>🔐</div>
                        <h3>Opening SSO login...</h3>
                        <p style={{ color: '#666' }}>
                            Please complete the login in the popup window
                        </p>
                    </div>
                ) : (
                    <>
                        <div style={{
                            backgroundColor: '#eff6ff',
                            border: '1px solid #bfdbfe',
                            padding: '16px',
                            borderRadius: '6px',
                            marginBottom: '24px'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                                <span style={{ fontSize: '20px', marginRight: '12px' }}>ℹ️</span>
                                <div style={{ fontSize: '14px', color: '#1e40af' }}>
                                    <strong>Next step:</strong> You'll be asked to log in using your company's SSO provider.
                                    After logging in, you'll be added to {invitation.tenant_name}.
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={handleAccept}
                            className="button button-primary"
                            style={{ width: '100%', padding: '16px', fontSize: '18px' }}
                        >
                            Accept Invitation & Login
                        </button>

                        <p style={{
                            textAlign: 'center',
                            marginTop: '20px',
                            fontSize: '14px',
                            color: '#666'
                        }}>
                            By accepting, you'll join {invitation.tenant_name}
                        </p>
                    </>
                )}
            </div>
        </div>
    );
};

export default InvitationAcceptPage;
