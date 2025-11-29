import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../../core/components/Card';
import { Button } from '../../../core/components/Button';
import firebaseAuthService from '../../../core/firebase/authService';
import api from '../../../core/api/b2bClient';

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
            const response = await fetch(`${API_BASE_URL}/api/activate/validate/${token}`);

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
            const response = await fetch(`${API_BASE_URL}/api/activate/tenant-info/${tenantInfo.tenant_id}`);
            const config = await response.json();

            console.log('🔐 Initiating SSO with:', config);

            // Set Firebase tenant context
            await firebaseAuthService.setTenantId(config.firebase_tenant_id);

            // Start SSO login with admin email as hint
            const result = await firebaseAuthService.signInWithOIDC(
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
            const response = await fetch(`${API_BASE_URL}/api/activate/complete`, {
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

    if (step === 'validating' || loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
                <Card className="w-full max-w-md">
                    <CardContent className="text-center py-12">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
                        <p className="text-gray-600">
                            {step === 'validating' ? 'Validating activation link...' : 'Processing...'}
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (step === 'error') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-pink-100">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle className="text-red-600">❌ Activation Error</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-gray-700 mb-4">{error}</p>
                        <Button onClick={() => navigate('/login')} variant="outline">
                            Back to Login
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (step === 'welcome') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
                <Card className="w-full max-w-2xl">
                    <CardHeader>
                        <CardTitle className="text-3xl text-center">
                            🎉 Welcome to {tenantInfo?.tenant_name}!
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                            <h3 className="font-semibold text-lg mb-2">Your SSO Account is Ready</h3>
                            <p className="text-gray-700 mb-4">
                                We've set up enterprise single sign-on for your organization.
                                Let's activate your account in 2 simple steps:
                            </p>
                            <ol className="list-decimal list-inside space-y-2 text-gray-700">
                                <li>Test your SSO login</li>
                                <li>Complete activation</li>
                            </ol>
                        </div>

                        <div className="bg-gray-50 rounded-lg p-4">
                            <p className="text-sm text-gray-600 mb-2">
                                <strong>Admin Email:</strong> {tenantInfo?.admin_email}
                            </p>
                            <p className="text-sm text-gray-600">
                                <strong>Domain:</strong> {tenantInfo?.domain}
                            </p>
                        </div>

                        <Button
                            onClick={startSSO}
                            className="w-full"
                            size="lg"
                            disabled={loading}
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
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-100 p-4">
                <Card className="w-full max-w-2xl">
                    <CardHeader>
                        <CardTitle className="text-3xl text-center text-green-700">
                            ✅ SSO Login Successful!
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                            <p className="text-lg text-gray-700 mb-4">
                                Your single sign-on is working correctly.
                            </p>
                            <p className="text-gray-600">
                                Click below to activate your account and start using the platform.
                            </p>
                        </div>

                        <Button
                            onClick={completeActivation}
                            className="w-full bg-green-600 hover:bg-green-700"
                            size="lg"
                            disabled={loading}
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
