import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TENANT_ROLES } from '../constants/roles';
import apiService from '../../../../core/api/b2bClient';
import firebaseAuthService from '../../../../core/firebase/authService';

function Dashboard() {
    const [user, setUser] = useState(null);
    const [firebaseUser, setFirebaseUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        loadUser();
    }, []);

    const loadUser = async () => {
        try {
            // Get Firebase user
            const fbUser = firebaseAuthService.getCurrentUser();
            setFirebaseUser(fbUser);

            // Get user info from backend
            const userInfo = await apiService.getCurrentUser();
            setUser(userInfo);
        } catch (err) {
            setError('Failed to load user information');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = async () => {
        try {
            await apiService.logout();
            navigate('/login');
        } catch (err) {
            console.error('Logout failed:', err);
        }
    };

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="loading-state">
                    <div className="spinner large"></div>
                    <p>Loading...</p>
                </div>
            </div>
        );
    }

    if (error || !user) {
        return (
            <div className="dashboard-container">
                <div className="error-state">
                    <span className="error-icon large">⚠️</span>
                    <p>{error || 'Failed to load user information'}</p>
                    <button onClick={() => navigate('/login')} className="secondary-button">
                        Return to Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <nav className="dashboard-nav">
                <div className="nav-content">
                    <div className="nav-brand">
                        <div className="logo-icon small">🔐</div>
                        <span className="brand-text">SSO Portal</span>
                    </div>
                    <button onClick={handleLogout} className="logout-button">
                        Logout
                    </button>
                </div>
            </nav>

            <main className="dashboard-main">
                <div className="welcome-card">
                    <div className="welcome-header">
                        <div className="user-avatar">
                            {user.name ? user.name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
                        </div>
                        <div className="welcome-text">
                            <h1>Welcome back{user.name ? `, ${user.name}` : ''}!</h1>
                            <p className="user-email">{user.email}</p>
                        </div>
                    </div>

                    <div className="info-grid">
                        <div className="info-item">
                            <div className="info-label">Organization</div>
                            <div className="info-value">{user.tenant_name}</div>
                        </div>
                        <div className="info-item">
                            <div className="info-label">User ID</div>
                            <div className="info-value">#{user.id}</div>
                        </div>
                        <div className="info-item">
                            <div className="info-label">Authentication</div>
                            <div className="info-value">
                                <span className="status-badge success">
                                    <span className="status-dot"></span>
                                    Active
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="dashboard-content">
                    {user.role === TENANT_ROLES.ADMIN && (
                        <div className="content-card" style={{
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            cursor: 'pointer'
                        }}
                            onClick={() => navigate('/invitations')}
                        >
                            <h2 style={{ color: 'white' }}>👥 Team Management</h2>
                            <p style={{ color: 'rgba(255,255,255,0.9)' }}>
                                Invite managers to join your organization. Manage pending and accepted invitations.
                            </p>
                            <div style={{
                                marginTop: '20px',
                                padding: '10px 20px',
                                background: 'rgba(255,255,255,0.2)',
                                borderRadius: '6px',
                                display: 'inline-block',
                                fontWeight: '600'
                            }}>
                                Manage Invitations →
                            </div>
                        </div>
                    )}

                    <div className="content-card">
                        <h2>🎉 Firebase Multi-Tenant SSO</h2>
                        <p>
                            You have successfully authenticated using Firebase Identity Platform
                            with multi-tenant support. Firebase handled the entire OIDC flow
                            including PKCE and state management.
                        </p>
                    </div>

                    <div className="content-card">
                        <h2>🔐 JWT Token Authentication</h2>
                        <p>
                            Your session is secured using Firebase ID tokens. Each API request
                            includes your JWT token in the Authorization header, validated by
                            the backend using Firebase Admin SDK.
                        </p>
                    </div>

                    <div className="content-card">
                        <h2>📊 Your Information</h2>
                        <div style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                            <p><strong>Email:</strong> {firebaseUser?.email}</p>
                            <p><strong>Firebase UID:</strong> {firebaseUser?.uid}</p>
                            <p><strong>Tenant ID:</strong> {firebaseUser?.tenantId || 'Default'}</p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

export default Dashboard;
