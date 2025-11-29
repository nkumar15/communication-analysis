import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import firebaseAuthService from '../../../core/firebase/authService';
import { auth } from '../../../core/firebase/config';

function PlatformLogin() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [config, setConfig] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const init = async () => {
            // Check if already authenticated
            const user = auth.currentUser;
            if (user) {
                navigate('/super-admin');
                return;
            }

            // Fetch platform configuration
            try {
                // Use platform API (port 8001) not B2B API (port 8000)
                const PLATFORM_API_URL = process.env.REACT_APP_PLATFORM_API_URL || 'http://localhost:8001';
                const response = await fetch(`${PLATFORM_API_URL}/api/platform/config`);

                if (!response.ok) {
                    throw new Error('Failed to load platform configuration');
                }

                const data = await response.json();
                console.log('✅ Loaded platform config:', data);
                setConfig(data);
            } catch (err) {
                console.error('❌ Failed to load platform config:', err);
                setError('Could not load system configuration. Please ensure backend is running.');
            } finally {
                setLoading(false);
            }
        };

        init();
    }, [navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        if (!config) {
            setError('System configuration not loaded. Please refresh the page.');
            setLoading(false);
            return;
        }

        try {
            // Validate email domain
            if (!email.includes('@platform.') && !email.includes('@system.')) {
                setError('Platform admin emails must use @platform.* or @system.* domain');
                setLoading(false);
                return;
            }

            console.log('🔍 Platform Login: Setting tenant ID:', config.firebase_tenant_id);

            // Set Firebase tenant context (system tenant)
            auth.tenantId = config.firebase_tenant_id;
            localStorage.setItem('firebase_tenant_id', config.firebase_tenant_id);

            console.log('🔍 Platform Login: Initiating OIDC with provider:', config.oidc_provider_id);

            // Sign in with OIDC
            const result = await firebaseAuthService.signInWithOIDC(config.oidc_provider_id, email);
            console.log('✅ Platform admin signed in:', result.user.email);

            // Get token and store it
            const idToken = await result.user.getIdToken();
            localStorage.setItem('token', idToken);

            console.log('✅ Platform admin authenticated successfully');

            // Redirect to super-admin (PlatformAdminRoute will verify role)
            navigate('/super-admin');

        } catch (err) {
            console.error('❌ Platform login error:', err);
            setError(err.message || 'Authentication failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    if (loading && !config) {
        return (
            <div style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
            }}>
                <div style={{ color: 'white', fontSize: '1.2rem' }}>
                    Loading configuration...
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
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        }}>
            <div style={{
                background: 'white',
                padding: '3rem',
                borderRadius: '12px',
                boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                width: '100%',
                maxWidth: '400px'
            }}>
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <div style={{ fontSize: '48px', marginBottom: '1rem' }}>⚡</div>
                    <h1 style={{ margin: 0, fontSize: '24px', color: '#1a1a2e' }}>Platform Admin</h1>
                    <p style={{ margin: '0.5rem 0 0 0', color: '#666' }}>SaaS Control Panel</p>
                    {config && (
                        <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.5rem' }}>
                            System: {config.tenant_name}
                        </p>
                    )}
                </div>

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '0.5rem',
                            fontWeight: 600,
                            color: '#333'
                        }}>
                            Platform Admin Email
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="admin@platform.net"
                            required
                            autoFocus
                            disabled={loading}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '2px solid #e0e0e0',
                                borderRadius: '6px',
                                fontSize: '16px',
                                transition: 'border-color 0.2s'
                            }}
                        />
                    </div>

                    {error && (
                        <div style={{
                            padding: '1rem',
                            background: '#fee',
                            border: '1px solid #fcc',
                            borderRadius: '6px',
                            color: '#c33',
                            marginBottom: '1rem'
                        }}>
                            ⚠️ {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading || !email}
                        style={{
                            width: '100%',
                            padding: '0.875rem',
                            background: loading ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            fontSize: '16px',
                            fontWeight: 600,
                            cursor: loading ? 'not-allowed' : 'pointer',
                            transition: 'transform 0.2s'
                        }}
                    >
                        {loading ? 'Authenticating...' : 'Sign In with SSO'}
                    </button>
                </form>

                <div style={{
                    marginTop: '2rem',
                    padding: '1rem',
                    background: '#f5f5f5',
                    borderRadius: '6px',
                    fontSize: '13px',
                    color: '#666',
                    textAlign: 'center'
                }}>
                    🔒 Platform administrators only
                </div>
            </div>
        </div>
    );
}

export default PlatformLogin;
