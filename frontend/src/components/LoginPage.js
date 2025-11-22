import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiService from '../services/api';
import firebaseAuthService from '../services/firebaseAuthService';

function LoginPage() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        // Check if user is already authenticated
        const checkAuth = async () => {
            const user = firebaseAuthService.getCurrentUser();
            if (user) {
                navigate('/');
            }
        };
        checkAuth();
    }, [navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            console.log('🔍 Step 1: Resolving tenant for email:', email);
            // Step 1: Resolve tenant from email domain
            const tenantInfo = await apiService.resolveTenant(email);
            console.log('✅ Tenant resolved:', tenantInfo);

            // Step 2: Set Firebase tenant context
            console.log('🔍 Step 2: Setting Firebase tenant ID:', tenantInfo.firebase_tenant_id);
            firebaseAuthService.setTenantId(tenantInfo.firebase_tenant_id);

            // Step 3: Initiate OIDC sign-in with redirect
            // Use the provider ID from tenant config, or fall back to 'oidc.generic'
            const providerId = tenantInfo.oidc_provider_id || 'oidc.generic';
            console.log('🔍 Step 3: Initiating OIDC sign-in with provider:', providerId);

            // Popup flow returns the result directly
            const result = await firebaseAuthService.signInWithOIDC(providerId);
            console.log('✅ User signed in:', result.user.email);

            // Get ID token directly from the result (more reliable than waiting for auth.currentUser)
            console.log('🔍 Step 4: Getting ID token for backend sync...');
            const idToken = await result.user.getIdToken();
            console.log('✅ Got ID token');

            // Sync user with backend using the token
            await apiService.syncUser();
            console.log('✅ User synced with backend');

            // Clear tenant ID from storage after successful login
            localStorage.removeItem('firebase_tenant_id');

            // Redirect to dashboard
            navigate('/');

        } catch (err) {
            console.error('❌ Login error:', err);
            setError(err.message || 'Authentication failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-card">
                <div className="login-header">
                    <div className="logo-container">
                        <div className="logo-icon">🔐</div>
                    </div>
                    <h1>Enterprise SSO Portal</h1>
                    <p className="subtitle">Sign in to your organization</p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="form-group">
                        <label htmlFor="email">Email Address</label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@company.com"
                            required
                            autoFocus
                            disabled={loading}
                            className="email-input"
                        />
                    </div>

                    {error && (
                        <div className="error-message">
                            <span className="error-icon">⚠️</span>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading || !email}
                        className="submit-button"
                    >
                        {loading ? (
                            <>
                                <span className="spinner"></span>
                                <span>Signing in...</span>
                            </>
                        ) : (
                            <>
                                <span>Continue with SSO</span>
                                <span className="arrow">→</span>
                            </>
                        )}
                    </button>
                </form>

                <div className="login-footer">
                    <p className="info-text">
                        Enter your work email to sign in with your organization's identity provider
                    </p>
                </div>
            </div>
        </div>
    );
}

export default LoginPage;
