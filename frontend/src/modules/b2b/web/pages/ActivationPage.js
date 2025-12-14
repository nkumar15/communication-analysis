import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../../../core/components/Card';
import { Button } from '../../../../core/components/Button';
import firebaseAuthService from '../../../../core/firebase/authService';
import api from '../../../../core/api/b2bClient';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const ActivationPage = () => {
    const { token } = useParams();
    const navigate = useNavigate();

    const [step, setStep] = useState('validating'); // validating, welcome, sso-login, complete, error
    const [tenantInfo, setTenantInfo] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [ssoWindow, setSsoWindow] = useState(null);

    useEffect(() => {
        validateToken();
    }, [token]);

    const validateToken = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/api/b2b/activation/validate/${token}`);

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Invalid activation token');
            }

            const data = await response.json();
            setTenantInfo(data);
            setStep('welcome');
        } catch (err) {
            console.error('Validation error:', err);
            setError(err.message || 'Invalid or expired activation link');
            setStep('error');
        } finally {
            setLoading(false);
        }
    };

    const startSSO = async () => {
        try {
            setLoading(true);
            setStep('sso-login');

            // Get Firebase tenant info
            const response = await fetch(`${API_BASE_URL}/api/b2b/activation/tenant-info/${tenantInfo.tenant_id}`);
            const config = await response.json();

            console.log('🔐 Initiating SSO with:', config);

            // Set Firebase tenant context
            await firebaseAuthService.setTenantId(config.firebase_tenant_id);

            // Start SSO login with admin email as hint
            // Use generic signIn dispatcher
            const providerType = config.provider_type || 'oidc';
            const result = await firebaseAuthService.signIn(
                providerType,
                config.oidc_provider_id,
                tenantInfo.admin_email
            );

            console.log('✅ SSO Login successful:', result.user.email);

            // Sync user with backend
            await api.syncUser();

            // Move to completion step
            setStep('complete');

        } catch (err) {
            console.error('SSO error:', err);
            setError(err.message || 'SSO login failed');
            setStep('error');
        } finally {
            setLoading(false);
        }
    };

    const completeActivation = async () => {
        try {
            setLoading(true);

            const headers = await api.getAuthHeaders();
            const response = await fetch(`${API_BASE_URL}/api/b2b/activation/complete`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ activation_token: token }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Activation failed');
            }

            const data = await response.json();
            console.log('✅ Activation complete:', data);

            // Redirect to dashboard
            setTimeout(() => {
                navigate('/dashboard');
            }, 2000);

        } catch (err) {
            console.error('Activation error:', err);
            setError(err.message || 'Failed to complete activation');
            setStep('error');
        } finally {
            setLoading(false);
        }
    };

    const pageStyle = {
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#eff6ff',
        padding: '24px'
    };

    if (step === 'validating' || loading) {
        return (
            <div style={pageStyle}>
                <Card style={{ width: '100%', maxWidth: '450px' }}>
                    <CardContent style={{ textAlign: 'center', padding: '48px' }}>
                        <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
                        <p style={{ color: '#4b5563' }}>
                            {step === 'validating' ? 'Validating activation link...' : 'Processing...'}
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (step === 'error') {
        return (
            <div style={{ ...pageStyle, backgroundColor: '#fef2f2' }}>
                <Card style={{ width: '100%', maxWidth: '450px' }}>
                    <CardHeader>
                        <CardTitle style={{ color: '#dc2626' }}>❌ Activation Error</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p style={{ color: '#374151', marginBottom: '24px' }}>{error}</p>
                        <Button onClick={() => navigate('/login')} variant="outline" style={{ width: '100%' }}>
                            Back to Login
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (step === 'welcome') {
        return (
            <div style={pageStyle}>
                <Card style={{ width: '100%', maxWidth: '600px' }}>
                    <CardHeader>
                        <CardTitle style={{ textAlign: 'center', fontSize: '28px' }}>
                            🎉 Welcome to {tenantInfo?.tenant_name}!
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div style={{
                            backgroundColor: '#eff6ff',
                            border: '1px solid #bfdbfe',
                            borderRadius: '8px',
                            padding: '24px',
                            marginBottom: '24px'
                        }}>
                            <h3 style={{ fontWeight: '600', fontSize: '18px', marginBottom: '8px', color: '#1e3a8a' }}>Your SSO Account is Ready</h3>
                            <p style={{ color: '#374151', marginBottom: '16px' }}>
                                We've set up enterprise single sign-on for your organization.
                                Let's activate your account in 2 simple steps:
                            </p>
                            <ol style={{ listStyleType: 'decimal', listStylePosition: 'inside', color: '#374151', paddingLeft: '8px' }}>
                                <li style={{ marginBottom: '8px' }}>Test your SSO login</li>
                                <li>Complete activation</li>
                            </ol>
                        </div>

                        <div style={{ backgroundColor: '#f9fafb', borderRadius: '8px', padding: '16px', marginBottom: '24px' }}>
                            <p style={{ fontSize: '14px', color: '#4b5563', marginBottom: '8px' }}>
                                <strong>Admin Email:</strong> {tenantInfo?.admin_email}
                            </p>
                            <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>
                                <strong>Domain:</strong> {tenantInfo?.domain}
                            </p>
                        </div>

                        <Button
                            onClick={startSSO}
                            size="lg"
                            disabled={loading}
                            style={{ width: '100%' }}
                        >
                            Get Started →
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (step === 'complete') {
        return (
            <div style={{ ...pageStyle, backgroundColor: '#f0fdf4' }}>
                <Card style={{ width: '100%', maxWidth: '600px' }}>
                    <CardHeader>
                        <CardTitle style={{ textAlign: 'center', color: '#15803d' }}>
                            ✅ SSO Login Successful!
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div style={{
                            backgroundColor: '#f0fdf4',
                            border: '1px solid #bbf7d0',
                            borderRadius: '8px',
                            padding: '24px',
                            textAlign: 'center',
                            marginBottom: '24px'
                        }}>
                            <p style={{ fontSize: '18px', color: '#374151', marginBottom: '16px' }}>
                                Your single sign-on is working correctly.
                            </p>
                            <p style={{ color: '#4b5563', margin: 0 }}>
                                Click below to activate your account and start using the platform.
                            </p>
                        </div>

                        <Button
                            onClick={completeActivation}
                            size="lg"
                            disabled={loading}
                            style={{ width: '100%', backgroundColor: '#16a34a' }}
                        >
                            {loading ? 'Activating...' : 'Activate Account'}
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return null;
};

export default ActivationPage;
