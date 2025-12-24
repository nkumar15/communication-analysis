import { useState, useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { auth } from '../firebase/config';

function PlatformAdminRoute({ children }) {
    const [isAuthorized, setIsAuthorized] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const checkPermission = async () => {
            try {
                // E2E Test Backdoor: Check for mock JWT
                const e2eToken = sessionStorage.getItem('firebaseToken');
                if (e2eToken && e2eToken.includes('mock_signature')) {
                    console.log('🧪 E2E: Bypassing Platform admin check with mock JWT');
                    setIsAuthorized(true);
                    setLoading(false);
                    return;
                }

                // Wait for Firebase auth to initialize
                const currentUser = auth.currentUser;

                if (!currentUser) {
                    console.log('No Firebase user logged in');
                    setIsAuthorized(false);
                    setLoading(false);
                    return;
                }

                // Get fresh Firebase token
                const token = await currentUser.getIdToken();

                // Store token for API calls
                localStorage.setItem('token', token);

                // Fetch user details from PLATFORM admin endpoint (not regular auth endpoint)
                const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';
                const response = await fetch(`${API_URL}/api/platform/auth/me`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    console.error('Failed to fetch user:', response.status);
                    setIsAuthorized(false);
                    setLoading(false);
                    return;
                }

                const user = await response.json();
                console.log('User role:', user.role);

                if (user && user.role === 'platform_admin') {
                    setIsAuthorized(true);
                } else {
                    setIsAuthorized(false);
                }
            } catch (error) {
                console.error('Error checking platform admin permission:', error);
                setIsAuthorized(false);
            } finally {
                setLoading(false);
            }
        };

        // Listen for auth state changes
        const unsubscribe = auth.onAuthStateChanged((user) => {
            if (user) {
                checkPermission();
            } else {
                checkPermission(); // Still check for E2E backdoor even without Firebase user
            }
        });

        return () => unsubscribe();
    }, []);

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100vh',
                background: '#1a1a2e'
            }}>
                <div style={{
                    width: '50px',
                    height: '50px',
                    border: '5px solid rgba(108, 92, 231, 0.3)',
                    borderTop: '5px solid #6c5ce7',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                }}></div>
                <p style={{ marginTop: '1rem', color: '#a0a0b0' }}>Verifying privileges...</p>
            </div>
        );
    }

    if (!isAuthorized) {
        // Redirect to platform login (use /login for standalone portal, /platform-login for combined app)
        return <Navigate to="/login" replace />;
    }

    // Support both nested routes (Outlet) and children pattern
    return children ? children : <Outlet />;
}

export default PlatformAdminRoute;
