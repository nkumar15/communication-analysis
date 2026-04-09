import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../../../core/components/Card';
import { Button } from '../../../../core/components/Button';
import firebaseAuthService from '../../../../core/firebase/authService';
import api from '../../../../core/api/b2bClient';

const ActivationPage = () => {
    const { token } = useParams();
    const navigate = useNavigate();

    const [step, setStep] = useState('validating'); // validating, welcome, sso-config, sso-login, complete, error
    const [tenantInfo, setTenantInfo] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [ssoWindow, setSsoWindow] = useState(null);
    const [ssoConfig, setSsoConfig] = useState({
        provider_type: 'oidc',
        oidc_client_id: '',
        oidc_client_secret: '',
        oidc_issuer: ''
    });
    const [isActivating, setIsActivating] = useState(false); // ✅ Prevent double-click

    useEffect(() => {
        validateToken();
    }, [token]);

    const validateToken = async () => {
        try {
            setLoading(true);
            const data = await api.validateActivationToken(token);
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

    const handleConfigChange = (e) => {
        const { name, value } = e.target;
        setSsoConfig(prev => ({ ...prev, [name]: value }));
    };

    const submitSSOConfig = async () => {
        try {
            setLoading(true);

            const payload = {
                activation_token: token,
                provider_type: ssoConfig.provider_type,
                provider_config: {
                    client_id: ssoConfig.oidc_client_id,
                    client_secret: ssoConfig.oidc_client_secret,
                    issuer: ssoConfig.oidc_issuer
                },
                oidc_client_id: ssoConfig.oidc_client_id,
                oidc_client_secret: ssoConfig.oidc_client_secret,
                oidc_issuer: ssoConfig.oidc_issuer
            };

            const data = await api.setupActivationSSO(payload);
            console.log('✅ SSO configured:', data);

            // Proceed to SSO login
            await startSSO();

        } catch (err) {
            console.error('SSO config error:', err);

            // Check if SSO provider already exists (HTTP 409)
            if (err.message && err.message.includes('already configured')) {
                console.log('✅ SSO already configured, skipping to login step');
                // SSO already exists, proceed to login
                await startSSO();
                return;
            }

            // Other errors
            setError(err.message || 'Failed to configure SSO');
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
            const config = await api.getActivationTenantInfo(tenantInfo.tenant_id);

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
        if (isActivating) return; // ✅ Prevent double-click

        try {
            setIsActivating(true);
            setLoading(true);

            const data = await api.completeActivation(token);
            console.log('✅ Activation complete:', data);

            // ✅ Navigate immediately (no setTimeout)
            navigate('/dashboard', { replace: true });

        } catch (err) {
            console.error('Activation error:', err);
            setError(err.message || 'Failed to complete activation');
            setStep('error');
            setIsActivating(false); // Allow retry on error
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
                            <h3 style={{ fontWeight: '600', fontSize: '18px', marginBottom: '8px', color: '#1e3a8a' }}>Let's Set Up Your SSO</h3>
                            <p style={{ color: '#374151', marginBottom: '16px' }}>
                                Configure your organization's single sign-on provider to enable secure access for your team.
                            </p>
                            <ol style={{ listStyleType: 'decimal', listStylePosition: 'inside', color: '#374151', paddingLeft: '8px' }}>
                                <li style={{ marginBottom: '8px' }}>Configure SSO provider</li>
                                <li style={{ marginBottom: '8px' }}>Test SSO login</li>
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
                            onClick={() => setStep('sso-config')}
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

    if (step === 'sso-config') {
        const inputStyle = {
            width: '100%',
            padding: '10px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '14px',
            transition: 'border-color 0.2s',
        };

        const labelStyle = {
            display: 'block',
            marginBottom: '6px',
            fontSize: '14px',
            fontWeight: '500',
            color: '#374151'
        };

        return (
            <div style={pageStyle}>
                <Card style={{ width: '100%', maxWidth: '600px' }}>
                    <CardHeader>
                        <CardTitle style={{ fontSize: '24px' }}>
                            🔐 Configure SSO Provider
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={(e) => { e.preventDefault(); submitSSOConfig(); }}>
                            <div style={{ marginBottom: '20px' }}>
                                <label style={labelStyle}>
                                    Provider Type <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <select
                                    name="provider_type"
                                    value={ssoConfig.provider_type}
                                    onChange={handleConfigChange}
                                    required
                                    style={inputStyle}
                                >
                                    <option value="oidc">OIDC (Generic)</option>
                                    <option value="google">Google Workspace</option>
                                    <option value="microsoft">Microsoft Azure AD</option>
                                </select>
                            </div>

                            <div style={{ marginBottom: '20px' }}>
                                <label style={labelStyle}>
                                    Client ID <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <input
                                    type="text"
                                    name="oidc_client_id"
                                    value={ssoConfig.oidc_client_id}
                                    onChange={handleConfigChange}
                                    placeholder="Enter your OIDC client ID"
                                    required
                                    style={inputStyle}
                                />
                            </div>

                            <div style={{ marginBottom: '20px' }}>
                                <label style={labelStyle}>
                                    Client Secret <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <input
                                    type="password"
                                    name="oidc_client_secret"
                                    value={ssoConfig.oidc_client_secret}
                                    onChange={handleConfigChange}
                                    placeholder="Enter your OIDC client secret"
                                    required
                                    style={inputStyle}
                                />
                            </div>

                            <div style={{ marginBottom: '24px' }}>
                                <label style={labelStyle}>
                                    Issuer URL <span style={{ color: '#ef4444' }}>*</span>
                                </label>
                                <input
                                    type="url"
                                    name="oidc_issuer"
                                    value={ssoConfig.oidc_issuer}
                                    onChange={handleConfigChange}
                                    placeholder="https://your-provider.com"
                                    required
                                    style={inputStyle}
                                />
                            </div>

                            <div style={{ display: 'flex', gap: '12px' }}>
                                <Button
                                    type="button"
                                    onClick={() => setStep('welcome')}
                                    variant="outline"
                                    disabled={loading}
                                    style={{ flex: 1 }}
                                >
                                    Back
                                </Button>
                                <Button
                                    type="submit"
                                    disabled={loading}
                                    style={{ flex: 2 }}
                                >
                                    {loading ? 'Configuring...' : 'Configure & Test SSO →'}
                                </Button>
                            </div>
                        </form>
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
                            disabled={loading || isActivating}
                            style={{ width: '100%', backgroundColor: '#16a34a' }}
                        >
                            {isActivating ? 'Redirecting...' : (loading ? 'Activating...' : 'Activate Account')}
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return null;
};

export default ActivationPage;
